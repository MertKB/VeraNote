# ui/styles.py
import json

PALETTES = {
    "Koyu Gece": {
        "bg_main": "#131314",
        "bg_card": "#1E1F22",
        "bg_sidebar": "#18191B",
        "bg_input": "#282A2E",
        "border_color": "#2F3136",
        "border_focus": "#8AB4F8",
        "accent_color": "#1A73E8",
        "accent_hover": "#1557B0",
        "accent_light": "#004A77",
        "text_main": "#E3E3E3",
        "text_muted": "#9AA0A6",
        "text_light": "#C2E7FF",
        "card_img_bg": "#18191B",
        "card_hover": "#25272C",
        "card_selected": "#192231",
        "card_selected_hover": "#1F2B3E"
    },
    "Derin Mor": {
        "bg_main": "#120E16",
        "bg_card": "#1D1625",
        "bg_sidebar": "#17121C",
        "bg_input": "#2A2033",
        "border_color": "#33253E",
        "border_focus": "#D7AEF5",
        "accent_color": "#A061D8",
        "accent_hover": "#8049B6",
        "accent_light": "#432B5B",
        "text_main": "#EAE5ED",
        "text_muted": "#B5A9BC",
        "text_light": "#F0E4FF",
        "card_img_bg": "#17121C",
        "card_hover": "#251D2F",
        "card_selected": "#281838",
        "card_selected_hover": "#331E48"
    },
    "Okyanus Mavisi": {
        "bg_main": "#06131D",
        "bg_card": "#0E1E2B",
        "bg_sidebar": "#091724",
        "bg_input": "#14293A",
        "border_color": "#1B3449",
        "border_focus": "#00E5FF",
        "accent_color": "#00B0FF",
        "accent_hover": "#0091EA",
        "accent_light": "#00365C",
        "text_main": "#E0F2F1",
        "text_muted": "#80CBC4",
        "text_light": "#E0F7FA",
        "card_img_bg": "#0B1823",
        "card_hover": "#14293A",
        "card_selected": "#10324D",
        "card_selected_hover": "#164164"
    }
}

def adjust_brightness(hex_color, factor):
    # factor > 1 to lighten, < 1 to darken
    hex_color = hex_color.lstrip('#')
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return "#" + hex_color

def is_light(hex_color):
    hex_color = hex_color.lstrip('#')
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return ((r * 299) + (g * 587) + (b * 114)) / 1000 >= 128
    except Exception:
        return False

def get_palette(theme_name="Koyu Gece", custom_colors=None):
    """Returns a dictionary of theme colors for the specified theme or custom colors."""
    if theme_name in ["Özel Tema", "Custom"]:
        if isinstance(custom_colors, str):
            try:
                custom_colors = json.loads(custom_colors)
            except Exception:
                custom_colors = None
        if not isinstance(custom_colors, dict):
            custom_colors = {}
            
        bg_main = custom_colors.get("bg_main", "#131314")
        bg_card = custom_colors.get("bg_card", "#1E1F22")
        accent_color = custom_colors.get("accent_color", "#1A73E8")
        
        custom_border = custom_colors.get("border_color")
        custom_input = custom_colors.get("bg_input")
        custom_sidebar = custom_colors.get("bg_sidebar")
        custom_text_main = custom_colors.get("text_main")
        custom_text_muted = custom_colors.get("text_muted")
        
        light_theme = is_light(bg_card)
        
        def parse_rgb(hex_c):
            h = hex_c.lstrip('#')
            try:
                return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            except Exception:
                return 10, 11, 13
        
        cr, cg, cb = parse_rgb(bg_card)
        ar, ag, ab = parse_rgb(accent_color)
        
        if not light_theme:
            # Dark theme smart derivation - ensure minimum contrast even on pure black (#000000)
            border_r = min(255, int(cr * 1.25 + 34))
            border_g = min(255, int(cg * 1.25 + 36))
            border_b = min(255, int(cb * 1.25 + 42))
            border_color = custom_border if custom_border else f"#{border_r:02X}{border_g:02X}{border_b:02X}"
            
            in_r = min(255, int(cr * 1.2 + 20))
            in_g = min(255, int(cg * 1.2 + 21))
            in_b = min(255, int(cb * 1.2 + 24))
            bg_input = custom_input if custom_input else f"#{in_r:02X}{in_g:02X}{in_b:02X}"
            
            bg_sidebar = custom_sidebar if custom_sidebar else bg_card
            card_img_bg = custom_colors.get("card_img_bg") or bg_card
            
            hov_r = min(255, int(cr * 1.15 + 12))
            hov_g = min(255, int(cg * 1.15 + 12))
            hov_b = min(255, int(cb * 1.15 + 14))
            card_hover = f"#{hov_r:02X}{hov_g:02X}{hov_b:02X}"
            
            sel_r = min(255, int(cr * 0.8 + ar * 0.2))
            sel_g = min(255, int(cg * 0.8 + ag * 0.2))
            sel_b = min(255, int(cb * 0.8 + ab * 0.2))
            card_selected = f"#{sel_r:02X}{sel_g:02X}{sel_b:02X}"
            
            sel_hov_r = min(255, int(cr * 0.7 + ar * 0.3))
            sel_hov_g = min(255, int(cg * 0.7 + ag * 0.3))
            sel_hov_b = min(255, int(cb * 0.7 + ab * 0.3))
            card_selected_hover = f"#{sel_hov_r:02X}{sel_hov_g:02X}{sel_hov_b:02X}"
            
            text_main = custom_text_main if custom_text_main else "#E3E3E3"
            text_muted = custom_text_muted if custom_text_muted else "#9AA0A6"
        else:
            # Light theme smart derivation
            border_r = max(0, int(cr * 0.82))
            border_g = max(0, int(cg * 0.82))
            border_b = max(0, int(cb * 0.82))
            border_color = custom_border if custom_border else f"#{border_r:02X}{border_g:02X}{border_b:02X}"
            
            in_r = max(0, int(cr * 0.94))
            in_g = max(0, int(cg * 0.94))
            in_b = max(0, int(cb * 0.94))
            bg_input = custom_input if custom_input else f"#{in_r:02X}{in_g:02X}{in_b:02X}"
            
            bg_sidebar = custom_sidebar if custom_sidebar else bg_card
            card_img_bg = custom_colors.get("card_img_bg") or bg_card
            
            hov_r = max(0, int(cr * 0.95))
            hov_g = max(0, int(cg * 0.95))
            hov_b = max(0, int(cb * 0.95))
            card_hover = f"#{hov_r:02X}{hov_g:02X}{hov_b:02X}"
            
            sel_r = min(255, int(cr * 0.85 + ar * 0.15))
            sel_g = min(255, int(cg * 0.85 + ag * 0.15))
            sel_b = min(255, int(cb * 0.85 + ab * 0.15))
            card_selected = f"#{sel_r:02X}{sel_g:02X}{sel_b:02X}"
            
            sel_hov_r = min(255, int(cr * 0.75 + ar * 0.25))
            sel_hov_g = min(255, int(cg * 0.75 + ag * 0.25))
            sel_hov_b = min(255, int(cb * 0.75 + ab * 0.25))
            card_selected_hover = f"#{sel_hov_r:02X}{sel_hov_g:02X}{sel_hov_b:02X}"
            
            text_main = custom_text_main if custom_text_main else "#1A1A1A"
            text_muted = custom_text_muted if custom_text_muted else "#5F6368"

        border_focus = adjust_brightness(accent_color, 1.2)
        accent_hover = adjust_brightness(accent_color, 0.85)
        accent_light = adjust_brightness(accent_color, 0.35 if not light_theme else 0.85)
        text_light = adjust_brightness(accent_color, 1.4 if not light_theme else 0.5)
        
        return {
            "bg_main": bg_main,
            "bg_card": bg_card,
            "bg_sidebar": bg_sidebar,
            "bg_input": bg_input,
            "border_color": border_color,
            "border_focus": border_focus,
            "accent_color": accent_color,
            "accent_hover": accent_hover,
            "accent_light": accent_light,
            "text_main": text_main,
            "text_muted": text_muted,
            "text_light": text_light,
            "card_img_bg": card_img_bg,
            "card_hover": card_hover,
            "card_selected": card_selected,
            "card_selected_hover": card_selected_hover
        }
    return PALETTES.get(theme_name, PALETTES["Koyu Gece"])

def get_stylesheet(theme_name="Koyu Gece", custom_colors=None):
    p = get_palette(theme_name, custom_colors)
    return f"""
QMainWindow {{
    background-color: {p['bg_main']};
    color: {p['text_main']};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

/* ScrollBar Styling */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 2px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {p['border_color']};
    min-height: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['border_focus']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    border: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 10px;
    margin: 2px 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {p['border_color']};
    min-width: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {p['border_focus']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    border: none;
}}

/* Splitter and Separator handles */
QSplitter::handle {{
    background-color: {p['border_color']};
    width: 4px;
    height: 4px;
}}
QSplitter::handle:hover {{
    background-color: {p['border_focus']};
}}

QMainWindow::separator {{
    background-color: {p['border_color']};
    width: 4px;
    height: 4px;
}}
QMainWindow::separator:hover {{
    background-color: {p['border_focus']};
}}

/* Sidebar Widget */
#SidebarWidget {{
    background-color: {p.get('bg_sidebar', p['bg_card'])};
    border-right: 1px solid {p['border_color']};
}}

/* Sidebar elements */
#SidebarTitle {{
    color: {p['text_main']};
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding: 8px 4px;
}}

QLineEdit {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_main']};
    padding: 8px 12px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border: 2px solid {p['border_focus']};
    background-color: {p['bg_card']};
}}

/* General Buttons */
QPushButton {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 20px; /* Rounded pill style */
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
}}
QPushButton:pressed {{
    background-color: {p['accent_color']};
}}

#NewNoteBtn, #NewLibBtn {{
    background-color: {p['accent_color']};
    color: white;
    border: none;
    border-radius: 20px;
    font-weight: bold;
    font-size: 14px;
    text-align: left;
    padding-left: 20px;
}}
#NewNoteBtn:hover, #NewLibBtn:hover {{
    background-color: {p['accent_hover']};
}}

QPushButton#HeaderAddBtn, QPushButton#EmptyTrashBtn {{
    background-color: {p['accent_color']};
    color: white;
    border: 1px solid {p['accent_color']};
    border-radius: 20px !important;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 13px;
    text-align: center;
}}
QPushButton#HeaderAddBtn:hover {{
    background-color: {p['accent_hover']};
    border-color: {p['accent_hover']};
}}
QPushButton#EmptyTrashBtn:hover {{
    background-color: #C02E26;
    border-color: #C02E26;
}}

/* Home, Notes & Settings Buttons in Sidebar */
#HomeBtn, #AgendaBtn, #AllNotesBtn, #TrashBtn, #SettingsBtn {{
    background-color: transparent;
    border: none;
    color: {p['text_main']};
    text-align: left;
    border-radius: 10px;
    transition: background-color 0.2s ease, color 0.2s ease;
}}

#HomeBtn QLabel, #AgendaBtn QLabel, #AllNotesBtn QLabel, #TrashBtn QLabel, #SettingsBtn QLabel {{
    color: {p['text_main']};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
    transition: color 0.2s ease;
}}

#HomeBtn:hover, #AgendaBtn:hover, #AllNotesBtn:hover, #TrashBtn:hover, #SettingsBtn:hover {{
    background-color: {p['bg_input']};
    color: white;
}}

#HomeBtn:hover QLabel, #AgendaBtn:hover QLabel, #AllNotesBtn:hover QLabel, #TrashBtn:hover QLabel, #SettingsBtn:hover QLabel {{
    color: white;
}}

#HomeBtn:pressed, #AgendaBtn:pressed, #AllNotesBtn:pressed, #TrashBtn:pressed, #SettingsBtn:pressed {{
    background-color: {p['border_color']};
    color: white;
}}

#HomeBtn:pressed QLabel, #AgendaBtn:pressed QLabel, #AllNotesBtn:pressed QLabel, #TrashBtn:pressed QLabel, #SettingsBtn:pressed QLabel {{
    color: white;
}}

#HomeBtn[active="true"], #AgendaBtn[active="true"], #AllNotesBtn[active="true"], #TrashBtn[active="true"], #SettingsBtn[active="true"] {{
    background-color: {p['accent_light']};
    border-left: 4px solid {p['border_focus']};
    border-radius: 8px;
}}

#HomeBtn[active="true"] QLabel, #AgendaBtn[active="true"] QLabel, #AllNotesBtn[active="true"] QLabel, #TrashBtn[active="true"] QLabel, #SettingsBtn[active="true"] QLabel {{
    color: {p['text_light']};
    font-weight: bold;
}}

/* Sidebar Collapse Toggle Button */
#SidebarCollapseBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
}}
#SidebarCollapseBtn:hover {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
}}
#SidebarCollapseBtn:pressed {{
    background-color: {p['border_color']};
}}

#ModelsHeaderBtn, #LibHeaderBtn {{
    background-color: transparent;
    border: none;
    color: #B5A9BC;
    text-align: left;
    border-radius: 8px;
}}
#ModelsHeaderBtn:hover, #LibHeaderBtn:hover {{
    background-color: {p['bg_input']};
    color: white;
}}
#ModelsHeaderBtn:hover QLabel, #LibHeaderBtn:hover QLabel {{
    color: white;
}}
#ModelsHeaderBtn[active="true"], #LibHeaderBtn[active="true"] {{
    background-color: {p['accent_light']};
    border-left: 4px solid {p['border_focus']};
    border-radius: 8px;
}}
#ModelsHeaderBtn[active="true"] QLabel, #LibHeaderBtn[active="true"] QLabel {{
    color: {p['text_light']};
    font-weight: bold;
}}

/* Navigation Rail (Collapsed Sidebar) Responsive Symmetrical Styling */
QPushButton[rail_mode="true"] {{
    padding: 0px !important;
    text-align: center !important;
    border-radius: 10px !important;
    margin: 0px !important;
}}

QPushButton#NewNoteBtn[rail_mode="true"], QPushButton#NewLibBtn[rail_mode="true"] {{
    padding-left: 0px !important;
    text-align: center !important;
    border-radius: 10px !important;
}}

QPushButton[rail_mode="true"][active="true"] {{
    background-color: {p['accent_light']} !important;
    border: 1px solid {p['border_focus']} !important;
    border-left: 1px solid {p['border_focus']} !important;
    border-radius: 10px !important;
}}

/* Close button in Detail Panel */
#CloseBtn {{
    background-color: transparent;
    border: none;
    font-size: 16px;
    color: {p['text_muted']};
    border-radius: 4px;
}}
#CloseBtn:hover {{
    color: {p['text_main']};
    background-color: {p['bg_input']};
}}

/* Save & Delete buttons in Detail Panel */
#SaveBtn, #DeleteNoteBtn {{
    border-radius: 20px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
    min-height: 20px;
}}
#SaveBtn:disabled {{
    background-color: {p['bg_input']};
    color: {p['text_muted']};
    border: 1px solid {p['border_color']};
}}
#SaveBtn:enabled {{
    background-color: {p['accent_color']};
    color: white;
    border: none;
}}
#SaveBtn:enabled:hover {{
    background-color: {p['accent_hover']};
}}

#DeleteNoteBtn {{
    background-color: #D32F2F;
    color: white;
    border: none;
}}
#DeleteNoteBtn:hover {{
    background-color: #B71C1C;
}}
#DeleteNoteBtn:disabled {{
    background-color: {p['bg_input']};
    color: {p['text_muted']};
    border: 1px solid {p['border_color']};
}}

/* List Widgets for Sidebar list items */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    background-color: transparent;
    color: {p['text_muted']};
    padding: 6px 12px;
    min-height: 28px;
    border-radius: 8px;
    margin-bottom: 2px;
}}
QListWidget::item:hover {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
}}
QListWidget::item:selected {{
    background-color: {p['accent_light']};
    color: {p['text_light']};
    font-weight: 600;
}}

/* Welcome Screen */
#WelcomeWidget {{
    background-color: {p['bg_main']};
}}

#WelcomeTitle {{
    color: {p['text_muted']};
    font-size: 32px;
    font-weight: 400;
}}

#WelcomeTextEdit {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 16px;
    color: {p['text_main']};
    padding: 16px;
    font-size: 15px;
    line-height: 20px;
}}
#WelcomeTextEdit:focus {{
    border: 1px solid {p['border_focus']};
}}

/* Model Card Grid Area */
#LibraryViewWidget {{
    background-color: {p['bg_main']};
}}

#GridScrollArea {{
    background-color: transparent;
    border: none;
}}

#NotesGridContainer, #LibraryGridContainer, #WorkflowGridContainer, #SidebarContainer {{
    background: transparent;
    border: none;
}}

/* Model Card */
#ModelCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 14px;
}}
#ModelCard:hover {{
    border: 1px solid {p['border_focus']};
    background-color: {p.get('card_hover', p['bg_input'])};
}}
#ModelCard[selected="true"] {{
    background-color: {p.get('card_selected', p['accent_light'])};
    border: 2px solid {p['accent_color']};
}}
#ModelCard[selected="true"]:hover {{
    border: 2px solid {p['border_focus']};
    background-color: {p.get('card_selected_hover', p['accent_hover'])};
}}

#CardImageLabel {{
    background-color: {p.get('card_img_bg', p['bg_card'])};
    border-top-left-radius: 13px;
    border-top-right-radius: 13px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}

#CardInfoPanel {{
    background-color: {p['bg_card']};
    border-top: 1px solid {p['border_color']};
    border-bottom-left-radius: 13px;
    border-bottom-right-radius: 13px;
}}

#CardTitle {{
    font-size: 13px;
    font-weight: bold;
    color: {p['text_main']};
    background: transparent;
}}

#CardFilename {{
    font-size: 11px;
    color: {p['text_muted']};
    background: transparent;
}}

#WarningBadge {{
    background-color: rgba(249, 168, 37, 0.9);
    color: #131314;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 4px;
    border-radius: 4px;
}}

#CardArchBadge {{
    background-color: rgba(20, 21, 24, 0.85);
    border: 1px solid {p['accent_color']};
    border-radius: 4px;
    color: {p['text_light']};
    font-size: 10px;
    font-weight: bold;
    padding: 1px 5px;
}}

#WorkflowArchBadge {{
    background-color: {p['accent_color']};
    color: #FFFFFF;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}}

QPushButton#CardFavBtn {{
    background-color: transparent;
    border: none;
    color: #6B7280;
    font-size: 18px;
    font-weight: bold;
    padding: 0px;
    margin: 0px;
}}
QPushButton#CardFavBtn:hover {{
    color: #F59E0B;
}}
QPushButton#CardFavBtn[favorite="true"] {{
    color: #F59E0B;
}}

QPushButton#CardSelectBtn {{
    background-color: rgba(255, 255, 255, 0.22);
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 6px;
    color: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0px;
    margin: 0px;
}}
QPushButton#CardSelectBtn:hover {{
    background-color: rgba(255, 255, 255, 0.35);
    border-color: rgba(255, 255, 255, 0.6);
}}
QPushButton#CardSelectBtn[selected="true"] {{
    background-color: #2563EB;
    border: 1px solid #60A5FA;
    color: #FFFFFF;
}}
QPushButton#CardSelectBtn[selected="true"]:hover {{
    background-color: #1D4ED8;
    border-color: #93C5FD;
}}


/* Detail Panel */
#DetailPanelWidget {{
    background-color: {p.get('bg_sidebar', p['bg_card'])};
    border-left: 1px solid {p['border_color']};
}}

#DetailTitle {{
    font-size: 20px;
    font-weight: bold;
    color: {p['text_main']};
}}

#DetailWordLabel {{
    font-weight: bold;
    color: {p['border_focus']};
    font-size: 13px;
}}

/* Trigger word pill */
#TriggerPill {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    color: {p['text_main']};
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
}}
#TriggerPill:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
}}

#TriggerPill:pressed {{
    background-color: {p['accent_light']};
    color: {p['text_light']};
}}

/* Settings Dialog */
QDialog {{
    background-color: {p['bg_card']};
    color: {p['text_main']};
}}

#SettingsScrollArea {{
    background: transparent;
    border: none;
}}

#SettingsContentWidget {{
    background: transparent;
}}

#SettingsBottomBar {{
    background-color: {p.get('bg_sidebar', p['bg_card'])};
    border-top: 1px solid {p['border_color']};
}}

/* Favorites Header Toggle Button */
#FavToggleBtn {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    color: {p['text_muted']};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
}}
#FavToggleBtn:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
    color: {p['text_main']};
}}
#FavToggleBtn:checked {{
    background-color: rgba(255, 215, 0, 0.16);
    border: 1px solid #FFD700;
    color: #FFD700;
    font-weight: bold;
}}
#FavToggleBtn:checked:hover {{
    background-color: rgba(255, 215, 0, 0.26);
    border-color: #FFE082;
    color: #FFF9C4;
}}

/* Notes View Widget */
#NotesViewWidget {{
    background-color: {p['bg_main']};
}}

/* Note Card */
#NoteCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}
#NoteCard:hover {{
    border: 1px solid {p['border_focus']};
    background-color: {p['bg_input']};
}}

#NoteCardTitle {{
    font-size: 16px;
    font-weight: bold;
    color: {p['text_main']};
}}

#NoteCardContent {{
    font-size: 11px;
    color: {p['text_muted']};
}}

#NoteCardImageLabel {{
    background-color: {p.get('card_img_bg', p['bg_card'])};
    border-top-left-radius: 11px;
    border-top-right-radius: 11px;
}}

QDockWidget {{
    background-color: {p['bg_card']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
}}

QDockWidget::title {{
    background-color: {p['bg_main']};
    text-align: left;
    padding: 6px;
    color: {p['text_main']};
    font-weight: bold;
}}

#AllNotesBadge {{
    background-color: {p['accent_light']};
    color: {p['text_light']};
    font-size: 11px;
    font-weight: bold;
    border-radius: 10px;
    border: none;
}}

#TrashBadge {{
    background-color: {p['accent_color']};
    color: white;
    font-size: 11px;
    font-weight: bold;
    border-radius: 10px;
    border: none;
}}

/* Corkboard & Welcome Screen Styles */
#CorkboardCard {{
    border-radius: 8px;
    border: 1px solid {p['border_color']};
}}
#CorkboardCard:hover {{
    border: 1px solid {p['border_focus']};
}}

#QuickNoteCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 10px;
}}

/* Detail Panel & Pill Styles */
#DetailPanel {{
    background-color: {p['bg_card']};
}}

#TriggerPill {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
}}
#TriggerPill:hover {{
    background-color: {p['accent_light']};
    border-color: {p['border_focus']};
    color: {p['text_light']};
}}

#TagPill {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}
#TagPill:hover {{
    border-color: {p['border_focus']};
}}

/* Agenda, Calendar & Daily Notes */
#AgendaPanel {{
    background-color: {p['bg_main']};
}}

#AgendaSectionContainer {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}

#AgendaCalendarWidget {{
    background-color: {p['bg_card']};
    border: none;
    color: {p['text_main']};
}}

#AgendaCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {p['bg_input']};
    border-bottom: 1px solid {p['border_color']};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-height: 40px;
}}

#AgendaCalendarWidget QToolButton {{
    color: {p['text_main']};
    background-color: transparent;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    padding: 4px 8px;
    margin: 2px;
}}
#AgendaCalendarWidget QToolButton:hover {{
    background-color: {p['accent_light']};
    color: {p['text_light']};
}}

#AgendaCalendarWidget QMenu {{
    background-color: {p['bg_card']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
}}

#AgendaCalendarWidget QSpinBox {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 4px;
}}

#AgendaCalendarWidget QTableView {{
    background-color: transparent;
    alternate-background-color: transparent;
    selection-background-color: {p['accent_color']};
    selection-color: #FFFFFF;
    gridline-color: transparent;
    outline: none;
    border: none;
}}

#AgendaCalendarWidget QTableView QHeaderView::section {{
    background-color: transparent;
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: bold;
    border: none;
    padding: 4px 0px;
}}

#DailyNoteEditor {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 10px;
    color: {p['text_main']};
    font-size: 14px;
    padding: 14px;
}}
#DailyNoteEditor:focus {{
    border: 1px solid {p['border_focus']};
}}

#TaskItemWidget {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
}}
#TaskItemWidget:hover {{
    border: 1px solid {p['border_focus']};
}}
#TaskDeleteBtn:hover {{
    background-color: #DC2626 !important;
    color: #FFFFFF !important;
}}

#RoutineItemWidget {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
}}
#RoutineItemWidget:hover {{
    border: 1px solid {p['border_focus']};
}}

#PriorityPill {{
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

/* Agenda Monthly Summary & Metrics Panel */
#AgendaMonthlySummaryPanel {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 10px;
    padding: 6px;
}}

#AgendaMetricCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    padding: 6px 8px;
}}
#AgendaMetricCard:hover {{
    border: 1px solid {p['border_focus']};
    background-color: {p['card_hover']};
}}

#AgendaMetricTitle {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: 600;
}}

#AgendaMetricValue {{
    color: {p['text_main']};
    font-size: 13px;
    font-weight: bold;
}}

#AgendaMetricSub {{
    color: {p['accent_color']};
    font-size: 10px;
    font-weight: 600;
}}

#AgendaMetricProgress {{
    border: none;
    border-radius: 2px;
    background-color: {p['border_color']};
    text-align: center;
    max-height: 4px;
}}
#AgendaMetricProgress::chunk {{
    background-color: {p['accent_color']};
    border-radius: 2px;
}}

/* Agenda Vertical Splitter between Calendar & Lower Scroll Area */
#AgendaVerticalSplitter::handle:vertical {{
    background-color: transparent;
    height: 8px;
    margin: 2px 20px;
    border-radius: 3px;
}}
#AgendaVerticalSplitter::handle:vertical:hover {{
    background-color: {p['border_focus']};
}}

/* Agenda Left Column Scroll Area */
#AgendaLeftScrollArea {{
    background: transparent;
    border: none;
}}
#AgendaLeftScrollArea > QWidget > QWidget {{
    background: transparent;
}}
#AgendaLeftScrollArea QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 5px;
    margin: 0px;
}}
#AgendaLeftScrollArea QScrollBar::handle:vertical {{
    background: {p['border_color']};
    min-height: 20px;
    border-radius: 2px;
}}
#AgendaLeftScrollArea QScrollBar::handle:vertical:hover {{
    background: {p['accent_color']};
}}
#AgendaLeftScrollArea QScrollBar::add-line:vertical,
#AgendaLeftScrollArea QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Upcoming Tasks Panel */
#UpcomingTasksPanel {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 10px;
    padding: 8px;
}}

#UpcomingTaskItemWidget {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 7px;
    padding: 6px 8px;
}}
#UpcomingTaskItemWidget:hover {{
    background-color: {p['card_hover']};
    border: 1px solid {p['border_focus']};
}}

#UpcomingDateBadge {{
    background-color: {p['bg_input']};
    color: {p['accent_color']};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: bold;
}}

#UpcomingEmptyLabel {{
    color: {p['text_muted']};
    font-size: 11px;
    padding: 12px 6px;
    font-style: italic;
}}
"""

def get_calendar_theme_config(theme_name="Koyu Gece", custom_colors=None):
    """
    Returns a unified, customizable dictionary for QCalendarWidget styling:
    - cell backgrounds (normal, other month, hover, today)
    - weekend/weekday day numbers and header colors
    - selection and today indicator colors
    - status indicator dots
    """
    p = get_palette(theme_name, custom_colors)
    if isinstance(custom_colors, str):
        try:
            custom_colors = json.loads(custom_colors)
        except Exception:
            custom_colors = {}
    if not isinstance(custom_colors, dict):
        custom_colors = {}

    # Extract customizable weekend colors
    w_header = custom_colors.get("cal_weekend_header", "#F472B6")
    w_text = custom_colors.get("cal_weekend_text", "#FB7185")

    return {
        # Cell backgrounds
        "cell_bg_normal": "transparent",
        "cell_bg_other_month": "transparent",
        "cell_bg_hover": p.get("card_hover", "#25272C"),
        "cell_bg_today": "transparent",
        
        # Selection
        "selection_bg": p.get("accent_color", "#1A73E8"),
        "selection_border": p.get("border_focus", "#8AB4F8"),
        "selection_text": "#FFFFFF",
        
        # Today
        "today_border": p.get("border_focus", "#8AB4F8"),
        
        # Day texts
        "text_weekday": p.get("text_main", "#E3E3E3"),
        "text_weekend": w_text,       # User-customizable weekend day numbers!
        "text_other_month": adjust_brightness(p.get("text_muted", "#9AA0A6"), 0.5),
        
        # Column headers
        "header_weekday": p.get("text_muted", "#9AA0A6"),
        "header_weekend": w_header,   # User-customizable weekend headers!
        
        # Status Dots
        "dot_pending_tasks": "#F59E0B",    # Amber
        "dot_completed_tasks": "#10B981",  # Emerald Green
        "dot_daily_note": "#38BDF8",       # Light Sky Blue
        
        # General palette reference
        "palette": p
    }

STYLE_SHEET = get_stylesheet("Koyu Gece")
