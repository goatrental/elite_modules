MENU_NAME = "Rozvoz"
MENU_URL = "/rozvoz"


def _claim_website(env):
    """Say which website the delivery belongs to.

    Installing the module cannot guess, so it takes the websites that already
    exist - on a normal install that is the one site the shop has. Anything
    created later stays untouched and the delivery will not appear on it.
    """
    websites = env["website"].search([])
    websites.write({"gelato_delivery_site": True})
    return websites


def _add_menu(env, websites):
    """Put the delivery page into the top menu of the delivery websites.

    The menu carries ``website_id`` on purpose - a menu without it shows up on
    every website in the database, which is wrong the moment a second site is
    added here.
    """
    Menu = env["website.menu"]
    for website in websites:
        exists = Menu.search(
            [("website_id", "=", website.id), ("url", "=", MENU_URL)], limit=1
        )
        if exists:
            continue
        top = Menu.search(
            [("website_id", "=", website.id), ("parent_id", "=", False)], limit=1
        )
        Menu.create({
            "name": MENU_NAME,
            "url": MENU_URL,
            "parent_id": top.id if top else False,
            "website_id": website.id,
            "sequence": 15,
        })


def _build_customers(env):
    """Give every order already in the database its customer row.

    Only matters where orders existed before the customer list did - a
    fresh shop has nothing to catch up on. Orders are walked oldest first
    so the name kept is the one the customer first gave.
    """
    orders = env["gelato.delivery.order"].search(
        [("customer_id", "=", False)], order="id"
    )
    orders._link_customer()


def post_init_hook(env):
    websites = _claim_website(env)
    _add_menu(env, websites)
    _build_customers(env)


def uninstall_hook(env):
    env["website.menu"].search([("url", "=", MENU_URL)]).unlink()
