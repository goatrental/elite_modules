/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";

/**
 * Turns delivery on and off, and sets the hours, from the same screen where
 * the staff flip the flavours every morning.
 *
 * The values live on the website record, which only an administrator may
 * write. The two ORM methods behind this bar run with sudo on purpose - the
 * point of the whole thing is that the person in the shop needs no Settings
 * access to close the delivery.
 */
export class GelatoDeliverySwitch extends Component {
    static template = "gelato_delivery.DeliverySwitch";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loaded: false,
            enabled: true,
            from: "",
            to: "",
            openNow: true,
            note: "",
        });
        onWillStart(() => this.load());
    }

    async load() {
        const data = await this.orm.call(
            "gelato.delivery.order",
            "gelato_switch_state",
            []
        );
        this._apply(data);
    }

    _apply(data) {
        this.state.enabled = data.enabled;
        this.state.from = this.constructor.toClock(data.order_from);
        this.state.to = this.constructor.toClock(data.order_to);
        this.state.openNow = data.open_now;
        this.state.note = data.note || "";
        this.state.loaded = true;
    }

    async _save(values) {
        const data = await this.orm.call(
            "gelato.delivery.order",
            "gelato_switch_write",
            [values]
        );
        this._apply(data);
    }

    onToggle() {
        this._save({ gelato_delivery_enabled: !this.state.enabled });
    }

    /**
     * The value is taken from the input rather than from the state, because
     * a two-way binding fires on the same `change` event as this handler and
     * the order is not guaranteed - it saved the previous value.
     */
    onHoursChange(which, ev) {
        const value = ev.target.value || "00:00";
        this.state[which] = value;
        this._save({
            gelato_order_from: this.constructor.toFloat(this.state.from),
            gelato_order_to: this.constructor.toFloat(this.state.to),
        });
    }

    get labels() {
        return {
            from: _t("Orders from"),
            to: _t("until"),
            hint: _t("Both 0:00 means around the clock."),
            toggle: _t("Switch the delivery on or off"),
        };
    }

    get statusLabel() {
        if (!this.state.enabled) {
            return _t("SWITCHED OFF - the website takes no orders");
        }
        if (!this.state.openNow) {
            // The switch being on is not the whole story: the hours close the
            // website too, and the green toggle on its own reads like
            // everything is running. Say plainly what is happening.
            return _t("CLOSED NOW - orders open at %s", this.state.from);
        }
        return _t("Taking orders, until %s", this.state.to);
    }

    /** 11.5 -> "11:30", for the two time inputs. */
    static toClock(value) {
        const hours = Math.floor(value || 0);
        const minutes = Math.round(((value || 0) - hours) * 60);
        return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    }

    /** "11:30" -> 11.5, the way the field is stored. */
    static toFloat(value) {
        const [hours, minutes] = (value || "0:00").split(":");
        return (parseInt(hours, 10) || 0) + (parseInt(minutes, 10) || 0) / 60;
    }
}

export class GelatoBoardController extends KanbanController {
    static template = "gelato_delivery.BoardWithSwitch";
    static components = {
        ...KanbanController.components,
        GelatoDeliverySwitch,
    };
}

registry.category("views").add("gelato_delivery_board", {
    ...kanbanView,
    Controller: GelatoBoardController,
});
