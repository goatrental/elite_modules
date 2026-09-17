import re
from datetime import timedelta

from odoo import _, fields, http
from odoo.http import request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GelatoRozvoz(http.Controller):
    """The public delivery page.

    An anonymous visitor has no rights on the delivery models, so everything
    is read and written through sudo(). In exchange, everything that arrives
    from the browser is validated again here - the price is always worked out
    on the server and never taken from the form.
    """

    # ------------------------------------------------------------------
    # Data for the page
    # ------------------------------------------------------------------
    def _page_values(self):
        website = request.website
        env = request.env
        flavors = env["gelato.flavor"].sudo().search([("available", "=", True)])
        boxes = env["gelato.delivery.box"].sudo().search([])
        addons = env["gelato.delivery.addon"].sudo().search([])

        orders_open, hours_note = website.gelato_orders_open()

        min_days = website.gelato_delivery_min_days or 0
        min_date = fields.Date.context_today(env["gelato.flavor"].sudo())
        if min_days:
            min_date += timedelta(days=min_days)

        return {
            "flavors": flavors,
            "flavors_by_category": self._group_by_category(flavors),
            "boxes": boxes,
            "addons": addons,
            "website": website,
            "delivery_enabled": website.gelato_delivery_enabled,
            "min_date": min_date.isoformat(),
            "promo_note": website.gelato_delivery_promo_note or "",
            "zones": env["gelato.delivery.zone"].sudo().search([]),
            "orders_open": orders_open,
            "hours_note": hours_note,
            "hours_label": website.gelato_order_hours_label(),
        }

    def _group_by_category(self, flavors):
        """Sort flavours into groups by category, skipping empty groups.

        The groups follow the order set on the categories themselves, not the
        order the flavours happen to come in. Otherwise moving one flavour
        between categories would reshuffle the whole page - the section of
        whichever flavour sorts first would jump to the top.

        Flavours with no category go last.
        """
        groups = []
        seen = {}
        for flavor in flavors:
            key = flavor.category_id.id or 0
            if key not in seen:
                seen[key] = {
                    "category": flavor.category_id,
                    "name": flavor.category_id.name or _("Other"),
                    "flavors": [],
                }
                groups.append(seen[key])
            seen[key]["flavors"].append(flavor)

        def order(group):
            category = group["category"]
            if not category:
                return (1, 0, "")
            return (0, category.sequence, category.name or "")

        return sorted(groups, key=order)

    @http.route(
        ["/rozvoz"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def rozvoz(self, **kwargs):
        return request.render("gelato_delivery.rozvoz", self._page_values())

    # ------------------------------------------------------------------
    # Promo code validation
    # ------------------------------------------------------------------
    @http.route(
        ["/rozvoz/overit-kod"],
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def overit_kod(self, code=None, **kwargs):
        promo = request.env["gelato.promo.code"].sudo().find_valid(code)
        if not promo:
            return {
                "valid": False,
                "message": _("We do not know this code, or it has expired."),
            }
        return {
            "valid": True,
            "code": promo.code,
            "discount_percent": promo.discount_percent,
            "message": _("The code is valid, a %g%% discount is applied.")
            % promo.discount_percent,
        }

    # ------------------------------------------------------------------
    # Address check against the drawn zones
    # ------------------------------------------------------------------
    @http.route(
        ["/rozvoz/overit-adresu"],
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def overit_adresu(self, address=None, postcode=None, **kwargs):
        result = self._locate_address(address, postcode)
        zone = result["zone"]

        if not result["checked"]:
            return {"valid": True, "message": "", "fee": None}

        if not result["located"]:
            if result["service_error"]:
                # Our map is down, not their typing. Let them order.
                return {
                    "valid": True,
                    "unsure": True,
                    "fee": None,
                    "message": _(
                        "We cannot check the address right now. Send the order "
                        "anyway - we will get back to you and agree the delivery."
                    ),
                }
            return {
                "valid": False,
                "fee": None,
                "message": _(
                    "We could not find that address. Please check the street "
                    "and the house number."
                ),
            }

        if not zone:
            return {
                "valid": False,
                "fee": None,
                "message": _(
                    "We do not drive there. Call us and we will see what we "
                    "can do."
                ),
            }

        return {
            "valid": True,
            "fee": zone.delivery_fee,
            "zone": zone.name,
            "message": _("We deliver to %(zone)s, delivery %(fee)s CZK.")
            % {"zone": zone.name, "fee": int(zone.delivery_fee)},
        }

    def _locate_address(self, address, postcode):
        """Put an address on the map and find its zone.

        ``checked`` is False when the shop has drawn no zones at all - then
        nothing is refused and the flat fee from the settings applies.
        """
        env = request.env
        Zone = env["gelato.delivery.zone"]
        empty = {
            "checked": False,
            "located": False,
            "service_error": False,
            "zone": Zone.sudo().browse(),
            "lat": 0.0,
            "lng": 0.0,
        }
        if not Zone.sudo().search_count([]):
            return empty

        found = env["gelato.geocode"].sudo().locate(address, postcode)
        if not found.get("found"):
            return dict(
                empty,
                checked=True,
                service_error=bool(found.get("service_error")),
            )

        lat = found["lat"]
        lng = found["lng"]
        return {
            "checked": True,
            "located": True,
            "service_error": False,
            "zone": Zone.zone_for(lat, lng),
            "lat": lat,
            "lng": lng,
        }

    # ------------------------------------------------------------------
    # Placing an order
    # ------------------------------------------------------------------
    @http.route(
        ["/rozvoz/objednat"],
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def objednat(self, **payload):
        website = request.website
        if not website.gelato_delivery_enabled:
            return {"success": False, "error": _("Delivery is paused right now.")}

        env = request.env
        errors = []

        # ---------- contact ----------
        customer_name = (payload.get("customer_name") or "").strip()
        customer_phone = (payload.get("customer_phone") or "").strip()
        customer_email = (payload.get("customer_email") or "").strip()
        delivery_address = (payload.get("delivery_address") or "").strip()

        if not customer_name:
            errors.append(_("Please fill in your name."))
        if not customer_phone:
            errors.append(_("Please fill in your phone number."))
        if not customer_email:
            errors.append(_("Please fill in your email."))
        elif not EMAIL_RE.match(customer_email):
            errors.append(_("That email address does not look right."))
        if not delivery_address:
            errors.append(_("Please fill in the delivery address."))

        # ---------- slot ----------
        delivery_time = payload.get("delivery_time") or "asap"
        valid_slots = dict(
            env["gelato.delivery.order"]._fields["delivery_time"].selection
        )
        if delivery_time not in valid_slots:
            delivery_time = "asap"

        today = fields.Date.context_today(env["gelato.flavor"].sudo())
        if delivery_time == "asap":
            # "As soon as possible" is today by definition. Whatever date the
            # browser sent is ignored, so an ASAP order can never end up
            # scheduled for next week.
            delivery_date = today
        else:
            delivery_date = self._parse_date(payload.get("delivery_date"))
            if not delivery_date:
                errors.append(_("Please pick a delivery date."))
            else:
                min_date = today
                if website.gelato_delivery_min_days:
                    min_date += timedelta(days=website.gelato_delivery_min_days)
                if delivery_date < min_date:
                    errors.append(_("That date is no longer available."))

        # Outside the ordering hours nothing goes through, however the form
        # got submitted. The page hides the form, but a stale tab could still
        # post - the hours have to hold here as well.
        orders_open, hours_note = website.gelato_orders_open()
        if not orders_open:
            errors.append(
                hours_note or _("We are not taking orders right now.")
            )

        # ---------- delivery zone ----------
        # The address goes on the map and the zone it lands in sets the fee.
        # An address the map does not know is sent back to be corrected: a
        # typo takes the customer two seconds to fix and would otherwise land
        # on the shop as an order nobody priced. The one case that still goes
        # through is the map being unreachable - that is our fault, not
        # theirs, and it must never stop an order.
        postcode = (payload.get("delivery_postcode") or "").strip()
        located = self._locate_address(delivery_address, postcode)
        zone = located["zone"]
        # An empty address was already complained about above; saying it is
        # also not on the map on top of that helps nobody.
        if (
            delivery_address
            and located["checked"]
            and not located["located"]
            and not located["service_error"]
        ):
            errors.append(
                _(
                    "We could not find that address. Please check the street "
                    "and the house number."
                )
            )
        if located["checked"] and located["located"] and not zone:
            errors.append(
                _(
                    "We do not deliver to that address. Give us a ring and we "
                    "will see what we can do."
                )
            )

        # ---------- thermal box ----------
        box = env["gelato.delivery.box"].sudo().browse(
            self._to_int(payload.get("box_id"))
        ).exists()
        if not box or not box.active:
            errors.append(_("Please choose a thermal box."))

        # ---------- flavours ----------
        flavor_ids = [
            self._to_int(value) for value in (payload.get("flavor_ids") or [])
        ]
        flavor_ids = [value for value in flavor_ids if value]
        flavors = env["gelato.flavor"].sudo().browse(flavor_ids).exists()

        # Never let through a flavour the staff has just switched off.
        unavailable = flavors.filtered(lambda f: not f.available)
        if unavailable:
            errors.append(
                _("We have run out of these today: %s. Please pick others.")
                % ", ".join(unavailable.mapped("name"))
            )
        if not flavors:
            errors.append(_("Please pick at least one flavour."))
        if box and box.max_flavors and len(flavors) > box.max_flavors:
            errors.append(
                _("You can pick at most %d flavours for this box.")
                % box.max_flavors
            )

        # ---------- extras ----------
        addon_commands, addon_total = self._build_addon_lines(
            payload.get("addons") or [], box, errors
        )

        if errors:
            return {"success": False, "error": " ".join(errors)}

        # ---------- amounts (always server side) ----------
        subtotal = box.price + addon_total
        promo = env["gelato.promo.code"].sudo().find_valid(payload.get("promo_code"))
        discount_percent = promo.discount_percent if promo else 0.0
        discount = subtotal * discount_percent / 100.0
        # The zone's own price wins; the flat fee from the settings is what
        # applies before any zone is drawn, or when the address is a mystery.
        if zone:
            base = subtotal
            if website.gelato_delivery_fee_base == "after_discount":
                base = subtotal - discount
            delivery_fee = zone.fee_for(base)
        else:
            delivery_fee = website.gelato_delivery_fee_for(subtotal, discount)

        if zone and zone.min_order and subtotal < zone.min_order:
            return {
                "success": False,
                "error": _(
                    "The minimum order for %(zone)s is %(amount)s CZK."
                )
                % {"zone": zone.name, "amount": int(zone.min_order)},
            }

        order = env["gelato.delivery.order"].sudo().create(
            {
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                "delivery_address": delivery_address,
                "delivery_postcode": postcode,
                "zone_id": zone.id if zone else False,
                "latitude": located["lat"],
                "longitude": located["lng"],
                "address_located": located["located"],
                "delivery_date": delivery_date,
                "delivery_time": delivery_time,
                "note": (payload.get("note") or "").strip(),
                "box_id": box.id,
                "box_price": box.price,
                "box_vat_rate": box.vat_rate,
                "flavor_ids": [(6, 0, flavors.ids)],
                "addon_line_ids": addon_commands,
                "promo_code_id": promo.id if promo else False,
                "discount_percent": discount_percent,
                "delivery_fee": delivery_fee,
                "delivery_vat_rate": website.gelato_delivery_fee_vat_rate,
                "website_id": website.id,
                "source": "website",
            }
        )

        if promo:
            promo.register_use()

        order._send_confirmation_email()

        return {
            "success": True,
            "order_ref": order.name,
            "message": _(
                "We have your order. We will get back to you to confirm the time."
            ),
            "tracking": order.tracking_payload(),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_addon_lines(self, raw_addons, box, errors):
        """Build the extra lines. Prices come from Odoo, never from the browser."""
        commands = []
        total = 0.0
        env = request.env
        bundles = env["gelato.delivery.addon"].sudo().browse()

        for raw in raw_addons:
            addon_id = self._to_int(
                raw.get("id") if isinstance(raw, dict) else raw
            )
            quantity = self._to_int(
                raw.get("quantity") if isinstance(raw, dict) else 1
            ) or 1
            if not addon_id or quantity <= 0:
                continue
            addon = env["gelato.delivery.addon"].sudo().browse(addon_id).exists()
            if not addon or not addon.active:
                errors.append(_("One of the extras is no longer available."))
                continue

            # A bundle is a discounted price for a box and an extra together.
            # It only makes sense with the box it was priced for - otherwise
            # the customer would get the discount on different goods.
            if addon.is_bundle:
                bundles |= addon
                if box and addon.bundle_box_id != box:
                    errors.append(
                        _("Bundle “%(bundle)s” only goes with the %(box)s box.")
                        % {
                            "bundle": addon.name,
                            "box": addon.bundle_box_id.name,
                        }
                    )
                    continue

            if addon.max_quantity and quantity > addon.max_quantity:
                quantity = addon.max_quantity
            commands.append(
                (
                    0,
                    0,
                    {
                        "addon_id": addon.id,
                        "quantity": quantity,
                        "price_unit": addon.price,
                        "vat_rate": addon.vat_rate,
                    },
                )
            )
            total += addon.price * quantity

        # Two bundles would mean two thermal boxes, but an order has only one.
        if len(bundles) > 1:
            errors.append(
                _("An order can contain only one bundle. You picked: %s.")
                % ", ".join(bundles.mapped("name"))
            )

        return commands, total

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _parse_date(value):
        if not value:
            return False
        try:
            return fields.Date.to_date(value)
        except (ValueError, TypeError):
            return False
