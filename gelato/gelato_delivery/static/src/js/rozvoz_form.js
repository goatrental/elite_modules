/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * The delivery form.
 *
 * The price worked out here is only a preview for the customer. The binding
 * figure is calculated by the server in the controller, so this code cannot
 * make an order cheaper.
 */
publicWidget.registry.GelatoRozvozForm = publicWidget.Widget.extend({
    selector: "#gelatoRozvozForm",
    events: {
        "change input[name='flavor_ids']": "_onFlavorChange",
        "change #gelatoBox": "_onBoxChange",
        "input .gl-rz-addon-qty": "_onAddonChange",
        "click #gelatoPromoBtn": "_onPromoClick",
        "input #gelatoPromo": "_onPromoInput",
        "change #gelatoTime": "_onTimeChange",
        "blur #gelatoAddress": "_onAddressBlur",
        "blur #gelatoPostcode": "_onAddressBlur",
        "submit": "_onSubmit",
    },

    start() {
        this.discountPercent = 0;
        this.promoCode = "";
        this.submitting = false;
        this.overLimit = false;
        this.zoneFee = null;

        const config = document.getElementById("gelatoConfig");
        this.deliveryFee = config ? parseFloat(config.dataset.fee || "0") : 0;
        this.freeFrom = config ? parseFloat(config.dataset.freeFrom || "0") : 0;
        this.feeBase = config ? config.dataset.feeBase || "before_discount" : "before_discount";

        this._prefillBoxFromHash();
        this._onTimeChange();
        this._recompute();
        return this._super(...arguments);
    },

    // ------------------------------------------------------------------
    // Delivery slot
    // ------------------------------------------------------------------
    /**
     * "As soon as possible" already means today, so asking for a date on top
     * of it is a question with only one right answer. The field is filled in
     * with today and greyed out instead - the customer still sees which day
     * we are coming, they just cannot contradict themselves.
     *
     * The server sets the date for an ASAP order anyway; this is only so the
     * form does not look like it is waiting for something.
     */
    _onTimeChange() {
        const time = this.el.querySelector("#gelatoTime");
        const date = this.el.querySelector("#gelatoDate");
        const field = this.el.querySelector("#gelatoDateField");
        const hint = this.el.querySelector("#gelatoDateHint");
        if (!time || !date || !field) {
            return;
        }

        const asap = time.value === "asap";
        if (asap) {
            // remember what the customer had picked, so switching back to a
            // slot does not silently lose it
            if (!date.disabled) {
                this._pickedDate = date.value;
            }
            date.value = this._today();
            date.readOnly = true;
            date.tabIndex = -1;
        } else {
            date.readOnly = false;
            date.tabIndex = 0;
            if (this._pickedDate) {
                date.value = this._pickedDate;
            }
        }
        date.classList.toggle("gl-rz-input-muted", asap);
        field.classList.toggle("gl-rz-field-muted", asap);
        if (hint) {
            hint.textContent = asap ? _t("We are coming today.") : "";
        }
    },

    _today() {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    },


    /**
     * The address decides both whether we drive there and what the delivery
     * costs, so it is worth answering while the customer is still on the
     * field rather than at the end. The server works it all out again on
     * submit; this only saves them filling in the rest for nothing.
     */
    async _onAddressBlur() {
        const input = this.el.querySelector("#gelatoAddress");
        const hint = this.el.querySelector("#gelatoAddressHint");
        if (!input || !hint) {
            return;
        }
        const address = input.value.trim();
        if (!address) {
            hint.textContent = "";
            hint.classList.remove("gl-rz-hint-warn");
            this.zoneFee = null;
            this._recompute();
            return;
        }
        const postcodeInput = this.el.querySelector("#gelatoPostcode");
        hint.textContent = _t("Looking the address up on the map...");
        hint.classList.remove("gl-rz-hint-warn");
        try {
            const result = await rpc("/rozvoz/overit-adresu", {
                address: address,
                postcode: postcodeInput ? postcodeInput.value.trim() : "",
            });
            hint.textContent = result.message || "";
            hint.classList.toggle("gl-rz-hint-warn", !result.valid || !!result.unsure);
            // A zone found means its own price, not the flat one.
            this.zoneFee = typeof result.fee === "number" ? result.fee : null;
            this._recompute();
        } catch {
            // the server checks it again on submit, so staying quiet is safe
            hint.textContent = "";
            hint.classList.remove("gl-rz-hint-warn");
            this.zoneFee = null;
            this._recompute();
        }
    },

    // ------------------------------------------------------------------
    // Picking a box from the cards above the form
    // ------------------------------------------------------------------
    _prefillBoxFromHash() {
        const select = this.el.querySelector("#gelatoBox");
        if (!select) {
            return;
        }
        document.querySelectorAll(".gl-rz-pick-box").forEach((link) => {
            link.addEventListener("click", () => {
                const boxId = link.dataset.boxId;
                if (boxId) {
                    select.value = boxId;
                    this._onBoxChange();
                }
            });
        });
    },

    // ------------------------------------------------------------------
    // Flavours
    // ------------------------------------------------------------------
    _selectedFlavors() {
        return Array.from(
            this.el.querySelectorAll("input[name='flavor_ids']:checked")
        ).map((input) => parseInt(input.value, 10));
    },

    _maxFlavors() {
        const option = this.el.querySelector("#gelatoBox option:checked");
        if (!option) {
            return 0;
        }
        return parseInt(option.dataset.maxFlavors || "0", 10);
    },

    _onFlavorChange() {
        this._enforceFlavorLimit();
        this._recompute();
    },

    _onBoxChange() {
        this._enforceFlavorLimit();
        this._syncBundleNote();
        this._recompute();
    },

    /**
     * Past the limit no further flavour can be ticked - the checkboxes lock,
     * so the customer can see straight away that the box is full.
     */
    _enforceFlavorLimit() {
        const max = this._maxFlavors();
        const checked = this._selectedFlavors().length;
        const hint = this.el.querySelector("#gelatoFlavorHint");
        const inputs = this.el.querySelectorAll("input[name='flavor_ids']");

        inputs.forEach((input) => {
            input.disabled = Boolean(max) && !input.checked && checked >= max;
            input.closest(".gl-rz-check").classList.toggle(
                "gl-rz-check-disabled",
                input.disabled
            );
        });

        // Switching to a smaller box can leave more flavours ticked than it
        // holds. Unticking them for the customer would be surprising, so we
        // just say it clearly and block the submit.
        this.overLimit = Boolean(max) && checked > max;

        if (!hint) {
            return;
        }
        if (this.overLimit) {
            hint.textContent = _t(
                "This box holds %(max)s flavours, but you picked %(checked)s. " +
                    "Remove %(extra)s, or choose a bigger box.",
                { max: max, checked: checked, extra: checked - max }
            );
        } else if (!max) {
            hint.textContent = checked
                ? _t("%s flavours picked.", checked)
                : _t("Pick at least one flavour.");
        } else if (checked === max) {
            hint.textContent = _t("The box is full: %(checked)s of %(max)s flavours.", {
                checked: checked,
                max: max,
            });
        } else {
            hint.textContent = _t("%(checked)s of %(max)s flavours picked.", {
                checked: checked,
                max: max,
            });
        }
        hint.classList.toggle("gl-rz-hint-warn", this.overLimit);
    },

    // ------------------------------------------------------------------
    // Extras
    // ------------------------------------------------------------------
    _selectedAddons() {
        const addons = [];
        this.el.querySelectorAll(".gl-rz-addon-qty").forEach((input) => {
            const quantity = parseInt(input.value || "0", 10);
            if (quantity > 0) {
                addons.push({
                    id: parseInt(input.dataset.addonId, 10),
                    quantity: quantity,
                    price: parseFloat(input.dataset.price || "0"),
                    bundleBox: input.dataset.bundleBox || "",
                    bundleName: input.dataset.bundleName || "",
                    input: input,
                });
            }
        });
        return addons;
    },

    _selectedBundles() {
        return this._selectedAddons().filter((addon) => addon.bundleBox);
    },

    /**
     * A bundle is priced for one specific box, so we switch to it right away.
     * The customer loses nothing they picked - only the box size lines up.
     */
    _onAddonChange(ev) {
        const input = ev.currentTarget;
        const bundles = this._selectedBundles();

        if (input.dataset.bundleBox && parseInt(input.value || "0", 10) > 0) {
            // Two bundles at once make no sense, an order has one box.
            bundles.forEach((other) => {
                if (other.input !== input) {
                    other.input.value = "0";
                }
            });
            const select = this.el.querySelector("#gelatoBox");
            if (select && select.value !== input.dataset.bundleBox) {
                select.value = input.dataset.bundleBox;
                this._enforceFlavorLimit();
            }
        }
        this._syncBundleNote();
        this._recompute();
    },

    /**
     * If the customer switches the box after picking a bundle, the bundle no
     * longer applies. Better to drop it and say why than to fail on submit.
     */
    _syncBundleNote() {
        const select = this.el.querySelector("#gelatoBox");
        const note = this.el.querySelector("#gelatoBundleNote");
        if (!select) {
            return;
        }
        const dropped = [];
        this._selectedBundles().forEach((bundle) => {
            if (bundle.bundleBox !== select.value) {
                bundle.input.value = "0";
                dropped.push(bundle.bundleName);
            }
        });
        if (note) {
            note.textContent = dropped.length
                ? _t(
                      "Bundle “%s” only goes with a different thermal box, " +
                          "so we removed it from your order.",
                      dropped.join(", ")
                  )
                : "";
            note.hidden = !dropped.length;
        }
        return dropped;
    },

    // ------------------------------------------------------------------
    // Price summary
    // ------------------------------------------------------------------
    _recompute() {
        const option = this.el.querySelector("#gelatoBox option:checked");
        const boxPrice = option ? parseFloat(option.dataset.price || "0") : 0;
        const addonTotal = this._selectedAddons().reduce(
            (sum, addon) => sum + addon.price * addon.quantity,
            0
        );

        const subtotal = boxPrice + addonTotal;
        const discount = (subtotal * this.discountPercent) / 100;
        const afterDiscount = subtotal - discount;

        // Same rule as on the server: depending on the setting, the free
        // delivery threshold is compared before or after the discount. Once
        // the address has landed in a zone, that zone's price replaces the
        // flat one - the server does exactly the same.
        const fee = this.zoneFee === null ? this.deliveryFee : this.zoneFee;
        let shipping = fee;
        if (!fee) {
            shipping = 0;
        } else if (this.freeFrom) {
            const base =
                this.feeBase === "after_discount" ? afterDiscount : subtotal;
            shipping = base >= this.freeFrom ? 0 : fee;
        }

        this._setText("gelatoSubtotal", this._money(subtotal));
        this._setText("gelatoDiscount", this._money(discount));
        this._setText("gelatoShipping", this._money(shipping));
        this._setText("gelatoTotal", this._money(afterDiscount + shipping));

        const discountRow = this.el.querySelector("#gelatoDiscountRow");
        if (discountRow) {
            discountRow.hidden = discount <= 0;
        }
        const discountLabel = this.el.querySelector("#gelatoDiscountLabel");
        if (discountLabel) {
            discountLabel.textContent = this.promoCode ? `(${this.promoCode})` : "";
        }
    },

    _money(value) {
        return Math.round(value).toLocaleString("cs-CZ");
    },

    _setText(id, text) {
        const node = this.el.querySelector(`#${id}`);
        if (node) {
            node.textContent = text;
        }
    },

    // ------------------------------------------------------------------
    // Promo code
    // ------------------------------------------------------------------
    _onPromoInput() {
        // Editing the code clears any discount already applied, so a stale
        // amount never stays on screen.
        if (this.discountPercent) {
            this.discountPercent = 0;
            this.promoCode = "";
            this._recompute();
        }
        this._setPromoMessage("", "");
    },

    async _onPromoClick() {
        const input = this.el.querySelector("#gelatoPromo");
        const code = input ? input.value.trim() : "";
        if (!code) {
            this._setPromoMessage(_t("Type in a promo code."), "error");
            return;
        }
        try {
            const result = await rpc("/rozvoz/overit-kod", { code: code });
            if (result.valid) {
                this.discountPercent = result.discount_percent;
                this.promoCode = result.code;
                this._setPromoMessage(result.message, "ok");
            } else {
                this.discountPercent = 0;
                this.promoCode = "";
                this._setPromoMessage(result.message, "error");
            }
        } catch {
            this.discountPercent = 0;
            this.promoCode = "";
            this._setPromoMessage(_t("We could not check the code, please try again."), "error");
        }
        this._recompute();
    },

    _setPromoMessage(text, kind) {
        const node = this.el.querySelector("#gelatoPromoMsg");
        if (!node) {
            return;
        }
        node.textContent = text;
        node.classList.toggle("gl-rz-promo-ok", kind === "ok");
        node.classList.toggle("gl-rz-promo-error", kind === "error");
    },

    // ------------------------------------------------------------------
    // Submitting
    // ------------------------------------------------------------------
    async _onSubmit(ev) {
        ev.preventDefault();
        if (this.submitting) {
            return;
        }

        const flavors = this._selectedFlavors();
        if (!flavors.length) {
            this._showError(_t("Pick at least one flavour."));
            return;
        }
        if (this.overLimit) {
            this._showError(
                _t(
                    "The chosen box holds %s flavours. Untick a few, or " +
                        "choose a bigger box.",
                    this._maxFlavors()
                )
            );
            return;
        }

        const payload = {
            customer_name: this._value("gelatoName"),
            customer_phone: this._value("gelatoPhone"),
            customer_email: this._value("gelatoEmail"),
            delivery_address: this._value("gelatoAddress"),
            delivery_postcode: this._value("gelatoPostcode"),
            delivery_date: this._value("gelatoDate"),
            delivery_time: this._value("gelatoTime"),
            note: this._value("gelatoNote"),
            box_id: this._value("gelatoBox"),
            flavor_ids: flavors,
            addons: this._selectedAddons().map((addon) => ({
                id: addon.id,
                quantity: addon.quantity,
            })),
            promo_code: this._value("gelatoPromo"),
        };

        this._setSubmitting(true);
        try {
            const result = await rpc("/rozvoz/objednat", payload);
            if (result.success) {
                this._trackPurchase(result.tracking);
                this._showSuccess(result);
            } else {
                this._showError(result.error || _t("The order could not be sent."));
            }
        } catch {
            this._showError(
                _t(
                    "The order could not be sent. Please try again, or call " +
                        "us on +420 773 09 58 09."
                )
            );
        } finally {
            this._setSubmitting(false);
        }
    },

    _value(id) {
        const node = this.el.querySelector(`#${id}`);
        return node ? node.value : "";
    },

    _setSubmitting(state) {
        this.submitting = state;
        const button = this.el.querySelector("#gelatoSubmit");
        if (button) {
            button.disabled = state;
            button.textContent = state ? _t("Sending...") : _t("Send the order");
        }
    },

    _showError(message) {
        const node = this.el.querySelector("#gelatoFormError");
        if (node) {
            node.textContent = message;
            node.hidden = false;
            node.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    },

    _showSuccess(result) {
        const success = document.getElementById("gelatoSuccess");
        if (!success) {
            return;
        }
        const message = document.getElementById("gelatoSuccessMsg");
        if (message) {
            message.textContent = result.message || "";
        }
        const reference = document.getElementById("gelatoSuccessRef");
        if (reference) {
            reference.textContent = result.order_ref || "";
        }
        this.el.hidden = true;
        success.hidden = false;
        success.scrollIntoView({ behavior: "smooth", block: "center" });
    },

    // ------------------------------------------------------------------
    // Conversion tracking
    // ------------------------------------------------------------------
    /**
     * The completed order event.
     *
     * The gelato_tracking module exposes window.gelatoTrack, but only once a
     * GTM or Pixel ID is filled in on the website settings. When nothing is
     * filled in the function does not exist and this is a no-op - nothing is
     * sent anywhere.
     */
    _trackPurchase(tracking) {
        if (!tracking) {
            return;
        }
        if (typeof window.gelatoTrack === "function") {
            window.gelatoTrack("purchase", tracking);
        }
    },
});

export default publicWidget.registry.GelatoRozvozForm;
