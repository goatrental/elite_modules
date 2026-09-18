"""Turn every old one-box order into a basket with one item.

Until now an order was a single thermal box written on the order itself,
with the extras on their own table. The website now sells several boxes in
one go, each with its own flavours, so everything moved onto
gelato.delivery.order.item. This copies the old orders over before the new
fields are loaded, so nothing that was already ordered is lost.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT table_name FROM information_schema.tables
         WHERE table_name = 'gelato_delivery_order_item'
    """)
    if cr.fetchone():
        _logger.info("gelato: items table already there, nothing to move")
        return

    cr.execute("""
        CREATE TABLE gelato_delivery_order_item (
            id serial PRIMARY KEY,
            order_id integer NOT NULL
                REFERENCES gelato_delivery_order(id) ON DELETE CASCADE,
            box_id integer REFERENCES gelato_delivery_box(id),
            addon_id integer REFERENCES gelato_delivery_addon(id),
            quantity integer NOT NULL DEFAULT 1,
            price_unit numeric,
            vat_rate numeric,
            price_subtotal numeric,
            label varchar,
            create_uid integer,
            create_date timestamp without time zone,
            write_uid integer,
            write_date timestamp without time zone
        )
    """)

    # The box that was on the order becomes the first item.
    cr.execute("""
        INSERT INTO gelato_delivery_order_item
            (order_id, box_id, quantity, price_unit, vat_rate, price_subtotal,
             create_date, write_date)
        SELECT id, box_id, 1, box_price, box_vat_rate, box_price, NOW(), NOW()
          FROM gelato_delivery_order
         WHERE box_id IS NOT NULL
         ORDER BY id
    """)
    moved_boxes = cr.rowcount

    # The flavours hung off the order; they now hang off that first item.
    cr.execute("""
        ALTER TABLE gelato_delivery_order_flavor
          ADD COLUMN IF NOT EXISTS item_id integer
              REFERENCES gelato_delivery_order_item(id) ON DELETE CASCADE
    """)
    cr.execute("""
        UPDATE gelato_delivery_order_flavor f
           SET item_id = i.id
          FROM gelato_delivery_order_item i
         WHERE i.order_id = f.order_id
           AND i.box_id IS NOT NULL
    """)
    # A flavour with no box to belong to cannot be kept - the column is
    # about to become required.
    cr.execute("DELETE FROM gelato_delivery_order_flavor WHERE item_id IS NULL")

    # Every extra becomes an item of its own.
    cr.execute("""
        SELECT table_name FROM information_schema.tables
         WHERE table_name = 'gelato_delivery_order_addon'
    """)
    moved_addons = 0
    if cr.fetchone():
        cr.execute("""
            INSERT INTO gelato_delivery_order_item
                (order_id, addon_id, quantity, price_unit, vat_rate,
                 price_subtotal, create_date, write_date)
            SELECT order_id, addon_id, quantity, price_unit, vat_rate,
                   price_subtotal, NOW(), NOW()
              FROM gelato_delivery_order_addon
             ORDER BY id
        """)
        moved_addons = cr.rowcount
        cr.execute("DROP TABLE gelato_delivery_order_addon")

    _logger.info(
        "gelato: moved %s boxes and %s extras onto order items",
        moved_boxes, moved_addons,
    )
