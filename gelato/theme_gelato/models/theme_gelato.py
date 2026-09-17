from odoo import models


class ThemeGelato(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_gelato_post_copy(self, mod):
        self.disable_view('website.footer_custom')
        # Odoo's optional header extras carry demo data - a US phone number and
        # a portal sign-in button. Neither belongs on the shop's header.
        self.disable_view('website.header_text_element')
        self.disable_view('website.header_call_to_action')
        self.disable_view("portal.user_sign_in")
