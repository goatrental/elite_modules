/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * The delivery form.
 *
 * An order is a basket. Thermal boxes, bundles and extras are three rows of
 * cards that swipe sideways; tapping a box asks which flavours go in it and
 * drops the result into the basket. The same box can go in twice with
 * different flavours, which is why the basket exists at all - one order used
 * to mean one box.
 *
 * The price worked out here is only a preview. The binding figure is
 * calculated by the server in the controller, so this code cannot make an
 * order cheaper.
 */
publicWidget.registry.GelatoRozvozForm = publicWidget.Widget.extend({
    selector: "#gelatoRozvozForm",
    events: {
        "click .gl-card": "_onCardClick",
        "click #gelatoPanel": "_onPanelBackdrop",
        "click #gelatoPanelClose": "_onPanelClose",
        "click .gl-opt": "_onPickFlavor",
        "click .gl-row-plus": "_onRowPlus",
        "click .gl-row-minus": "_onRowMinus",
        "click #gelatoAddToCart": "_onAddToCart",
        "click .gl-cart-plus": "_onCartPlus",
        "click .gl-cart-minus": "_onCartMinus",
        "click .gl-cart-drop": "_onCartDrop",
        "click #gelatoContinue": "_onContinue",
        "click #gelatoPromoBtn": "_onPromoClick",
        "input #gelatoPromo": "_onPromoInput",
        "blur #gelatoAddress": "_onAddressBlur",
        "blur #gelatoPostcode": "_onAddressBlur",
        "submit": "_onSubmit",
    },

    start() {
        this.cart = [];
        this.nextUid = 1;
        this.draft = null;
        this.flavorQty = {};
        this.submitting = false;
        this.zoneFee = null;
        this.zoneFreeFrom = null;
        this._forgetPromo();

        const config = document.getElementById("gelatoConfig");
        this.deliveryFee = config ? parseFloat(config.dataset.fee || "0") : 0;
        this.freeFrom = config ? parseFloat(config.dataset.freeFrom || "0") : 0;
        this.feeBase = config ? config.dataset.feeBase || "before_discount" : "before_discount";

        // Escape closes the open product the way every other dialog does.
        this._onKeyDown = (ev) => {
            if (ev.key === "Escape" && this.draft) {
                this._closePanel();
            }
        };
        document.addEventListener("keydown", this._onKeyDown);
        this._watchSliders();

        this._renderCart();
        this._recompute();
        return this._super(...arguments);
    },

    destroy() {
        document.removeEventListener("keydown", this._onKeyDown);
        clearTimeout(this.toastTimer);
        clearTimeout(this.toastHideTimer);
        return this._super(...arguments);
    },

    /**
     * Drop the "Swipe" hint off a row once it has been swiped.
     *
     * It is there to say the row keeps going sideways. Somebody who has
     * already moved it knows, and the hint sitting in the heading from
     * then on is just clutter. A row short enough to fit loses the hint
     * straight away - there is nothing to swipe.
     */
    _watchSliders() {
        for (const slider of this.el.querySelectorAll(".gl-slider")) {
            const label = slider.previousElementSibling;
            const hint = label && label.querySelector(".gl-swipe");
            if (!hint) {
                continue;
            }
            if (slider.scrollWidth <= slider.clientWidth + 4) {
                hint.classList.add("gl-swipe-done");
                continue;
            }
            slider.addEventListener(
                "scroll",
                () => hint.classList.add("gl-swipe-done"),
                { once: true, passive: true }
            );
        }
    },

    // ------------------------------------------------------------------
    // The product cards
    // ------------------------------------------------------------------
    /**
     * A box or a bundle holds gelato, so it opens the panel and asks what
     * goes in it. A bottle does not - one tap and it is in the basket.
     */
    _onCardClick(ev) {
        const card = ev.currentTarget;
        const parts = parseInt(card.dataset.parts || "0", 10);
        const product = {
            kind: card.dataset.kind,
            id: parseInt(card.dataset.id, 10),
            name: card.dataset.name || "",
            price: parseFloat(card.dataset.price || "0"),
            parts: parts,
        };
        if (!parts) {
            this._addToCart({ ...product, quantity: 1, flavors: {} });
            return;
        }
        this._openPanel(product, card);
    },

    // ------------------------------------------------------------------
    // Filling a box
    // ------------------------------------------------------------------
    /**
     * The card opens into its own screen: the picture large at the top and
     * the flavours underneath. Tapping a small card and having a box appear
     * somewhere further down the page read as nothing happening.
     */
    _openPanel(product, card) {
        this.draft = product;
        this.flavorQty = {};
        this.sourceCard = card;

        const panel = this.el.querySelector("#gelatoPanel");
        if (!panel) {
            return;
        }
        this._setText("gelatoPanelName", product.name);
        this._setText("gelatoPanelPrice", `${this._money(product.price)} Kč`);

        // What this one is, in full - the card clips the same line.
        const note = this.el.querySelector("#gelatoPanelNote");
        if (note) {
            note.textContent = card.dataset.note || "";
            note.hidden = !note.textContent;
        }

        // The picture is the one already on the card, badge left behind.
        const photo = this.el.querySelector("#gelatoPanelPhoto");
        const source = card.querySelector(".gl-card-photo");
        if (photo && source) {
            photo.innerHTML = source.innerHTML;
            const tag = photo.querySelector(".gl-card-tag");
            if (tag) {
                tag.remove();
            }
        }

        panel.hidden = false;
        this._renderQty();
        this._syncPartsHint();
        const dialog = panel.querySelector(".gl-panel-card");
        if (dialog) {
            dialog.scrollTop = 0;
        }
        this._zoomFrom(card);
    },

    /**
     * Grow the opened product out of the card that was tapped.
     *
     * The dialog is measured where it will end up and then played
     * backwards from the card's own place and size, so the two read as one
     * object rather than a box appearing out of nowhere.
     */
    _zoomFrom(card) {
        const panel = this.el.querySelector("#gelatoPanel");
        const dialog = panel.querySelector(".gl-panel-card");
        const backdrop = panel.querySelector(".gl-panel-backdrop");
        if (!dialog || !card.getBoundingClientRect || this._reducedMotion()) {
            return;
        }
        const from = card.getBoundingClientRect();
        const to = dialog.getBoundingClientRect();
        if (!to.width || !to.height) {
            return;
        }
        const scaleX = from.width / to.width;
        const scaleY = from.height / to.height;
        const shiftX = from.left + from.width / 2 - (to.left + to.width / 2);
        const shiftY = from.top + from.height / 2 - (to.top + to.height / 2);

        const ease = "cubic-bezier(.22,.72,.26,1)";
        dialog.animate(
            [
                {
                    transform: `translate(${shiftX}px, ${shiftY}px) scale(${scaleX}, ${scaleY})`,
                    opacity: 0.5,
                    borderRadius: "14px",
                },
                { transform: "none", opacity: 1, borderRadius: "18px" },
            ],
            { duration: 340, easing: ease }
        );
        if (backdrop) {
            backdrop.animate([{ opacity: 0 }, { opacity: 1 }], {
                duration: 260,
                easing: "ease-out",
            });
        }
    },

    _reducedMotion() {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    },

    _onPanelClose() {
        this._closePanel();
    },

    /** A tap on the dark area around the card closes it too. */
    _onPanelBackdrop(ev) {
        if (ev.target === ev.currentTarget) {
            this._closePanel();
        }
    },

    _closePanel() {
        this.draft = null;
        this.flavorQty = {};
        const panel = this.el.querySelector("#gelatoPanel");
        if (!panel || panel.hidden) {
            return;
        }
        let closed = false;
        const finish = () => {
            if (closed) {
                return;
            }
            closed = true;
            panel.hidden = true;
            this.sourceCard = null;
        };

        // Shrink back into the card it came out of. If anything is missing
        // - no card, no animation support - it simply closes.
        const dialog = panel.querySelector(".gl-panel-card");
        const backdrop = panel.querySelector(".gl-panel-backdrop");
        const card = this.sourceCard;
        if (!dialog || !card || !card.isConnected || this._reducedMotion()) {
            finish();
            return;
        }
        const from = card.getBoundingClientRect();
        const to = dialog.getBoundingClientRect();
        if (!to.width || !to.height) {
            finish();
            return;
        }
        const scaleX = from.width / to.width;
        const scaleY = from.height / to.height;
        const shiftX = from.left + from.width / 2 - (to.left + to.width / 2);
        const shiftY = from.top + from.height / 2 - (to.top + to.height / 2);

        if (backdrop) {
            backdrop.animate([{ opacity: 1 }, { opacity: 0 }], {
                duration: 200,
                easing: "ease-in",
                fill: "forwards",
            });
        }
        const closing = dialog.animate(
            [
                { transform: "none", opacity: 1, borderRadius: "18px" },
                {
                    transform: `translate(${shiftX}px, ${shiftY}px) scale(${scaleX}, ${scaleY})`,
                    opacity: 0,
                    borderRadius: "14px",
                },
            ],
            { duration: 240, easing: "cubic-bezier(.4,0,.8,.4)" }
        );
        closing.onfinish = finish;
        closing.oncancel = finish;
        // A timeline that never advances - a background tab, a browser
        // that skips animations - must not leave the overlay stuck open.
        setTimeout(finish, 400);
    },

    _handedOut() {
        return Object.values(this.flavorQty).reduce((sum, q) => sum + q, 0);
    },

    _flavorName(id) {
        const option = this.el.querySelector(`.gl-opt[data-flavor-id="${id}"]`);
        return option ? option.dataset.flavorName : "";
    },

    _setFlavorQty(id, amount) {
        if (amount > 0) {
            this.flavorQty[id] = amount;
        } else {
            delete this.flavorQty[id];
        }
    },

    /**
     * Write the counts back onto the list itself.
     *
     * There is nowhere else to look. A flavour that is in the box says how
     * many and carries its own plus and minus, so the box gets filled
     * without ever leaving the list - which is the whole point, because
     * the list is long and scrolling back to it after every pick was the
     * worst part of ordering.
     */
    _renderQty() {
        const left = this.draft ? this.draft.parts - this._handedOut() : 0;
        for (const row of this.el.querySelectorAll(".gl-opt-row")) {
            const counter = row.querySelector(".gl-opt-qty");
            if (!counter) {
                continue;
            }
            const quantity = this.flavorQty[row.dataset.flavorId] || 0;
            row.classList.toggle("gl-opt-taken", quantity > 0);
            counter.hidden = quantity === 0;
            counter.querySelector(".gl-qty-value").textContent = quantity;
            // A full box takes no more of anything. Saying so on the
            // buttons beats letting them be pressed and do nothing.
            counter.querySelector(".gl-row-plus").disabled = left <= 0;
            row.querySelector(".gl-opt").disabled = left <= 0 && quantity === 0;
        }
    },

    _onPickFlavor(ev) {
        const id = ev.currentTarget.dataset.flavorId;
        if (!this.draft || this._handedOut() >= this.draft.parts) {
            return;
        }
        this._setFlavorQty(id, (this.flavorQty[id] || 0) + 1);
        this._renderQty();
        this._syncPartsHint();
    },

    _onRowPlus(ev) {
        const id = ev.currentTarget.closest(".gl-opt-row").dataset.flavorId;
        if (!this.draft || this._handedOut() >= this.draft.parts) {
            return;
        }
        this._setFlavorQty(id, (this.flavorQty[id] || 0) + 1);
        this._renderQty();
        this._syncPartsHint();
    },

    _onRowMinus(ev) {
        const id = ev.currentTarget.closest(".gl-opt-row").dataset.flavorId;
        this._setFlavorQty(id, (this.flavorQty[id] || 0) - 1);
        this._renderQty();
        this._syncPartsHint();
    },

    /** Tell the customer how much of the box is still unspoken for. */
    _syncPartsHint() {
        const hint = this.el.querySelector("#gelatoPartsHint");
        if (!hint || !this.draft) {
            return;
        }
        const parts = this.draft.parts;
        const left = parts - this._handedOut();

        if (left > 0) {
            hint.textContent = _t("%(left)s of %(parts)s still to hand out.", {
                left: left,
                parts: parts,
            });
            hint.classList.add("gl-rz-hint-warn");
        } else {
            hint.textContent = _t("The box is full.");
            hint.classList.remove("gl-rz-hint-warn");
        }

        const confirm = this.el.querySelector("#gelatoAddToCart");
        if (confirm) {
            confirm.disabled = left !== 0;
        }
    },

    _onAddToCart() {
        if (!this.draft || this._handedOut() !== this.draft.parts) {
            return;
        }
        this._addToCart({ ...this.draft, quantity: 1, flavors: { ...this.flavorQty } });
        this._closePanel();
    },

    // ------------------------------------------------------------------
    // The basket
    // ------------------------------------------------------------------
    /** The same product with the same flavours is one line with a count. */
    _cartKey(entry) {
        const flavors = Object.entries(entry.flavors)
            .map(([id, q]) => `${id}:${q}`)
            .sort()
            .join(",");
        return `${entry.kind}-${entry.id}-${flavors}`;
    },

    _addToCart(entry) {
        const key = this._cartKey(entry);
        const existing = this.cart.find((line) => this._cartKey(line) === key);
        if (existing) {
            existing.quantity += entry.quantity;
        } else {
            this.cart.push({ ...entry, uid: this.nextUid++ });
        }
        this._renderCart();
        this._recompute();
        this._flashAdded();
    },

    /**
     * Say out loud that it went in.
     *
     * The order is listed further down the page, so from where the
     * customer is standing a tap changes nothing they can see. A second of
     * "Added" across the middle of the screen is the difference between
     * ordering once and ordering three times because nothing seemed to
     * happen. One word, no box around it - it is a confirmation, not a
     * thing to read.
     */
    _flashAdded() {
        const toast = this.el.querySelector("#gelatoToast");
        if (!toast) {
            return;
        }
        clearTimeout(this.toastTimer);
        toast.hidden = false;
        // Restart the animation even when one is still running, so a
        // second tap flashes again instead of sitting there.
        toast.classList.remove("gl-toast-in");
        void toast.offsetWidth;
        toast.classList.add("gl-toast-in");
        this.toastTimer = setTimeout(() => {
            // Dropping the class fades it out and lets it drift away.
            toast.classList.remove("gl-toast-in");
            this.toastHideTimer = setTimeout(() => {
                toast.hidden = true;
            }, 560);
        }, 1000);
    },

    _cartLine(ev) {
        const uid = parseInt(ev.currentTarget.closest(".gl-cart-line").dataset.uid, 10);
        return this.cart.find((line) => line.uid === uid);
    },

    _onCartPlus(ev) {
        const line = this._cartLine(ev);
        if (line) {
            line.quantity += 1;
            this._renderCart();
            this._recompute();
        }
    },

    _onCartMinus(ev) {
        const line = this._cartLine(ev);
        if (!line) {
            return;
        }
        line.quantity -= 1;
        if (line.quantity <= 0) {
            this.cart = this.cart.filter((other) => other !== line);
        }
        this._renderCart();
        this._recompute();
    },

    _onCartDrop(ev) {
        const line = this._cartLine(ev);
        this.cart = this.cart.filter((other) => other !== line);
        this._renderCart();
        this._recompute();
    },

    _flavorSummary(line) {
        return Object.entries(line.flavors)
            .map(([id, q]) => (q > 1 ? `${q}× ${this._flavorName(id)}` : this._flavorName(id)))
            .join(", ");
    },

    _renderCart() {
        const box = this.el.querySelector("#gelatoCart");
        const empty = this.el.querySelector("#gelatoCartEmpty");
        const foot = this.el.querySelector("#gelatoCartFoot");
        if (!box) {
            return;
        }
        box.innerHTML = "";

        for (const line of this.cart) {
            const row = document.createElement("div");
            row.className = "gl-cart-line";
            row.dataset.uid = line.uid;

            const body = document.createElement("span");
            body.className = "gl-cart-body";
            const name = document.createElement("span");
            name.className = "gl-cart-name";
            name.textContent = line.name;
            body.append(name);
            const flavors = this._flavorSummary(line);
            if (flavors) {
                const sub = document.createElement("span");
                sub.className = "gl-cart-sub";
                sub.textContent = flavors;
                body.append(sub);
            }

            const qty = document.createElement("span");
            qty.className = "gl-qty";
            qty.innerHTML =
                '<button type="button" class="gl-qty-btn gl-cart-minus">−</button>' +
                '<span class="gl-qty-value"></span>' +
                '<button type="button" class="gl-qty-btn gl-cart-plus">+</button>';
            qty.querySelector(".gl-qty-value").textContent = line.quantity;

            const price = document.createElement("span");
            price.className = "gl-cart-price";
            price.textContent = `${this._money(line.price * line.quantity)} Kč`;

            const drop = document.createElement("button");
            drop.type = "button";
            drop.className = "gl-cart-drop";
            drop.setAttribute("aria-label", _t("Remove"));
            drop.textContent = "×";

            row.append(body, qty, price, drop);
            box.append(row);
        }

        // The list itself is further down the page, so the bare total needs
        // saying how many things it covers.
        const things = this.cart.reduce((sum, line) => sum + line.quantity, 0);
        let count = "";
        if (things === 1) {
            count = _t("1 item ·");
        } else if (things < 5) {
            count = _t("%s items ·", things);
        } else if (things) {
            count = _t("%s items in total ·", things);
        }
        this._setText("gelatoCartCount", count);

        const filled = this.cart.length > 0;
        if (empty) {
            empty.hidden = filled;
        }
        if (foot) {
            foot.hidden = !filled;
        }
        if (!filled) {
            const checkout = this.el.querySelector("#gelatoCheckout");
            if (checkout) {
                checkout.hidden = true;
            }
        }
    },

    _onContinue() {
        if (!this.cart.length) {
            return;
        }
        const checkout = this.el.querySelector("#gelatoCheckout");
        if (checkout) {
            checkout.hidden = false;
            checkout.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    },

    // ------------------------------------------------------------------
    // Address
    // ------------------------------------------------------------------
    /**
     * The address decides both whether we drive there and what the delivery
     * costs, so it is worth answering while the customer is still on the
     * field rather than at the end.
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
            this.zoneFreeFrom = null;
            this._recompute();
            return;
        }
        const postcode = this.el.querySelector("#gelatoPostcode");
        hint.textContent = _t("Looking the address up on the map...");
        hint.classList.remove("gl-rz-hint-warn");
        try {
            const result = await rpc("/rozvoz/overit-adresu", {
                address: address,
                postcode: postcode ? postcode.value.trim() : "",
            });
            hint.textContent = result.message || "";
            hint.classList.toggle("gl-rz-hint-warn", !result.valid || !!result.unsure);
            this.zoneFee = typeof result.fee === "number" ? result.fee : null;
            // A zone can have its own free-from figure; without it the
            // preview would keep using the one from the settings.
            this.zoneFreeFrom =
                typeof result.free_from === "number" ? result.free_from : null;
            this._recompute();
        } catch {
            // the server checks it again on submit, so staying quiet is safe
            hint.textContent = "";
            hint.classList.remove("gl-rz-hint-warn");
            this.zoneFee = null;
            this.zoneFreeFrom = null;
            this._recompute();
        }
    },

    // ------------------------------------------------------------------
    // Promo code
    // ------------------------------------------------------------------
    _onPromoInput() {
        // Editing the code drops the discount until it is checked again.
        if (this.discountPercent) {
            this._forgetPromo();
            this._recompute();
        }
    },

    _forgetPromo() {
        this.discountPercent = 0;
        this.promoCode = "";
        this.promoScope = "all";
        this.promoBoxIds = [];
        this.promoAddonIds = [];
    },

    async _onPromoClick() {
        const input = this.el.querySelector("#gelatoPromo");
        const hint = this.el.querySelector("#gelatoPromoHint");
        const code = input ? input.value.trim() : "";
        if (!code) {
            return;
        }
        try {
            const result = await rpc("/rozvoz/overit-kod", { code: code });
            hint.textContent = result.message || "";
            hint.classList.toggle("gl-rz-hint-warn", !result.valid);
            if (result.valid) {
                this.discountPercent = result.discount_percent;
                this.promoCode = result.code;
                this.promoScope = result.scope || "all";
                this.promoBoxIds = result.box_ids || [];
                this.promoAddonIds = result.addon_ids || [];
            } else {
                this._forgetPromo();
            }
        } catch {
            hint.textContent = _t("We could not check the code. Try again.");
            hint.classList.add("gl-rz-hint-warn");
            this._forgetPromo();
        }
        this._recompute();
    },

    // ------------------------------------------------------------------
    // Price preview
    // ------------------------------------------------------------------
    _subtotal() {
        return this.cart.reduce((sum, line) => sum + line.price * line.quantity, 0);
    },

    /** Does the code that was entered come off this basket line? */
    _promoCovers(line) {
        if (this.promoScope === "all") {
            return true;
        }
        if (this.promoScope !== "products") {
            return false;
        }
        const ids = line.kind === "box" ? this.promoBoxIds : this.promoAddonIds;
        return (ids || []).includes(line.id);
    },

    _recompute() {
        const subtotal = this._subtotal();
        // The same order of operations as the controller: what the code
        // covers comes off the goods first, the fee is worked out on
        // that, and only a code aimed at the drive touches the fee.
        const percent = this.discountPercent / 100;
        let discount = this.cart
            .filter((line) => this._promoCovers(line))
            .reduce((sum, line) => sum + line.price * line.quantity, 0) * percent;
        const afterDiscount = subtotal - discount;

        // Same rule as on the server: the zone's own fee wins once the
        // address has landed in one, and the free delivery threshold is
        // compared before or after the discount depending on the setting.
        const fee = this.zoneFee === null ? this.deliveryFee : this.zoneFee;
        // The zone brings its own free-from figure once the address has
        // landed in one; before that the one from the settings applies.
        const freeFrom =
            this.zoneFreeFrom === null ? this.freeFrom : this.zoneFreeFrom;
        let shipping = fee;
        if (!fee) {
            shipping = 0;
        } else if (freeFrom) {
            const base = this.feeBase === "after_discount" ? afterDiscount : subtotal;
            shipping = base >= freeFrom ? 0 : fee;
        }
        if (this.promoScope === "delivery") {
            discount = shipping * percent;
        }

        this._setText("gelatoCartTotal", this._money(subtotal));
        this._setText("gelatoSubtotal", this._money(subtotal));
        this._setText("gelatoDiscount", this._money(discount));
        this._setText("gelatoShipping", this._money(shipping));
        // Not afterDiscount + shipping: a code for the drive changes the
        // discount only once the fee above is known.
        this._setText("gelatoTotal", this._money(subtotal - discount + shipping));

        const discountRow = this.el.querySelector("#gelatoDiscountRow");
        if (discountRow) {
            discountRow.hidden = discount <= 0;
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
    // Sending it
    // ------------------------------------------------------------------
    _value(id) {
        const node = this.el.querySelector(`#${id}`);
        return node ? node.value.trim() : "";
    },

    _setSubmitting(on) {
        this.submitting = on;
        const button = this.el.querySelector("#gelatoSubmit");
        if (button) {
            button.disabled = on;
        }
    },

    _showError(message) {
        const box = this.el.querySelector("#gelatoFormError");
        if (!box) {
            return;
        }
        box.textContent = message;
        box.hidden = false;
        box.scrollIntoView({ behavior: "smooth", block: "center" });
    },

    _showSuccess(result) {
        this.el.hidden = true;
        // "Put together your box" over a finished order reads as if
        // something still wants doing.
        const head = document.querySelector("#objednavka .gl-rz-head");
        if (head) {
            head.hidden = true;
        }
        const done = document.getElementById("gelatoRozvozDone");
        const ref = document.getElementById("gelatoOrderRef");
        if (ref) {
            ref.textContent = result.order_ref || "";
        }
        if (done) {
            done.hidden = false;
            done.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    },

    _trackPurchase(tracking) {
        if (!tracking) {
            return;
        }
        if (typeof window.gelatoTrack === "function") {
            window.gelatoTrack("purchase", tracking);
        }
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        if (this.submitting) {
            return;
        }
        const errorBox = this.el.querySelector("#gelatoFormError");
        if (errorBox) {
            errorBox.hidden = true;
        }
        if (!this.cart.length) {
            this._showError(_t("Your order is empty. Please pick something first."));
            return;
        }

        const payload = {
            customer_name: this._value("gelatoName"),
            customer_phone: this._value("gelatoPhone"),
            customer_email: this._value("gelatoEmail"),
            delivery_address: this._value("gelatoAddress"),
            delivery_postcode: this._value("gelatoPostcode"),
            delivery_city: this._value("gelatoCity"),
            note: this._value("gelatoNote"),
            items: this.cart.map((line) => ({
                kind: line.kind,
                id: line.id,
                quantity: line.quantity,
                flavors: Object.entries(line.flavors).map(([id, quantity]) => ({
                    id: parseInt(id, 10),
                    quantity: quantity,
                })),
            })),
            promo_code: this.promoCode || this._value("gelatoPromo"),
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
});

export default publicWidget.registry.GelatoRozvozForm;
