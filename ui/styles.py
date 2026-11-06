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
        "highlight_color": "#8AB4F8",
        "accent_color": "#1A73E8",
        "accent_hover": "#1557B0",
        "accent_light": "#004A77",
        "text_main": "#E3E3E3",
        "text_muted": "#9AA0A6",
        "text_light": "#C2E7FF",
        "card_img_bg": "#18191B",
        "card_hover": "#25272C",
        "card_selected": "#192231",
        "card_selected_hover": "#1F2B3E",
        "badge_bg": "#282A2E"
    },
    "Derin Mor": {
        "bg_main": "#120E16",
        "bg_card": "#1D1625",
        "bg_sidebar": "#17121C",
        "bg_input": "#2A2033",
        "border_color": "#33253E",
        "border_focus": "#D7AEF5",
        "highlight_color": "#D7AEF5",
        "accent_color": "#A061D8",
        "accent_hover": "#8049B6",
        "accent_light": "#432B5B",
        "text_main": "#EAE5ED",
        "text_muted": "#B5A9BC",
        "text_light": "#F0E4FF",
        "card_img_bg": "#17121C",
        "card_hover": "#251D2F",
        "card_selected": "#281838",
        "card_selected_hover": "#331E48",
        "badge_bg": "#2A2033"
    },
    "Okyanus Mavisi": {
        "bg_main": "#06131D",
        "bg_card": "#0E1E2B",
        "bg_sidebar": "#091724",
        "bg_input": "#14293A",
        "border_color": "#1B3449",
        "border_focus": "#00E5FF",
        "highlight_color": "#00E5FF",
        "accent_color": "#00B0FF",
        "accent_hover": "#0091EA",
        "accent_light": "#00365C",
        "text_main": "#E0F2F1",
        "text_muted": "#80CBC4",
        "text_light": "#E0F7FA",
        "card_img_bg": "#0B1823",
        "card_hover": "#14293A",
        "card_selected": "#10324D",
        "card_selected_hover": "#164164",
        "badge_bg": "#14293A"
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
            card_hover = custom_colors.get("card_hover") or (adjust_brightness(bg_input, 1.15) if custom_input else f"#{hov_r:02X}{hov_g:02X}{hov_b:02X}")
            
            sel_r = min(255, int(cr * 0.8 + ar * 0.2))
            sel_g = min(255, int(cg * 0.8 + ag * 0.2))
            sel_b = min(255, int(cb * 0.8 + ab * 0.2))
            card_selected = f"#{sel_r:02X}{sel_g:02X}{sel_b:02X}"
            
            sel_hov_r = min(255, int(cr * 0.7 + ar * 0.3))
            sel_hov_g = min(255, int(cg * 0.7 + ag * 0.3))
            sel_hov_b = min(255, int(cb * 0.7 + ab * 0.3))
            card_selected_hover = custom_colors.get("card_selected_hover") or f"#{sel_hov_r:02X}{sel_hov_g:02X}{sel_hov_b:02X}"
            
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

        custom_highlight = custom_colors.get("highlight_color")
        custom_border_focus = custom_colors.get("border_focus")
        custom_card_selected = custom_colors.get("card_selected")

        highlight_color = custom_highlight if custom_highlight else ("#8AB4F8" if not light_theme else "#1A73E8")
        border_focus = custom_border_focus if custom_border_focus else (highlight_color if custom_highlight else adjust_brightness(accent_color, 1.2))
        if custom_card_selected:
            card_selected = custom_card_selected

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
            "highlight_color": highlight_color,
            "accent_color": accent_color,
            "accent_hover": accent_hover,
            "accent_light": accent_light,
            "text_main": text_main,
            "text_muted": text_muted,
            "text_light": text_light,
            "card_img_bg": custom_colors.get("card_img_bg") or custom_colors.get("bg_input") or bg_card,
            "card_hover": card_hover,
            "card_selected": card_selected,
            "card_selected_hover": card_selected_hover,
            "badge_bg": custom_colors.get("badge_bg") or custom_colors.get("bg_input") or bg_input
        }
    return PALETTES.get(theme_name, PALETTES["Koyu Gece"])

def get_stylesheet(theme_name="Koyu Gece", custom_colors=None):
    p = get_palette(theme_name, custom_colors)
    sidebar_fg = "#1A1A1A" if is_light(p.get('bg_sidebar', p['bg_card'])) else "#FFFFFF"
    try:
        from utils.icon_manager import get_icons_dir
        icons_dir = get_icons_dir().replace('\\', '/')
    except Exception:
        icons_dir = "assets/icons"
    spin_up_icon = f"{icons_dir}/spin_up.png"
    spin_down_icon = f"{icons_dir}/spin_down.png"
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
    color: #FFFFFF;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 0.4px;
    padding: 0px 4px;
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

/* Global QComboBox */
QComboBox {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_main']};
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {p['border_focus']};
}}
QComboBox:focus {{
    border: 1.5px solid {p['border_focus']};
}}
QComboBox::drop-down {{
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {p['bg_card']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 6px;
    selection-background-color: {p['card_selected']};
    selection-color: {p['text_main']};
    outline: none;
    padding: 4px;
}}

/* Global SpinBoxes (Steps, CFG, Denoise, LoRA Strength, etc.) */
QSpinBox, QDoubleSpinBox {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 6px;
    color: {p['text_main']};
    min-height: 28px;
    padding-left: 8px;
    padding-right: 24px;
    font-size: 13px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {p['border_focus']};
}}

QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
    color: {p['text_main']};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    right: 0px;
    width: 20px;
    height: 14px;
    background-color: {p['bg_card']};
    border-left: 1px solid {p['border_color']};
    border-bottom: 1px solid {p['border_color']};
    border-top-right-radius: 5px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: {p['border_color']};
}}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
    background-color: {p['accent_light']};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({spin_up_icon});
    width: 8px;
    height: 8px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    right: 0px;
    width: 20px;
    height: 14px;
    background-color: {p['bg_card']};
    border-left: 1px solid {p['border_color']};
    border-bottom-right-radius: 5px;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {p['border_color']};
}}

QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background-color: {p['accent_light']};
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({spin_down_icon});
    width: 8px;
    height: 8px;
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

#NewNoteBtn, #NewLibBtn, #NewNotebookBtn {{
    background-color: {p['accent_color']};
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    font-size: 14px;
    padding: 0px;
    margin: 0px;
}}
#NewNoteBtn:hover, #NewLibBtn:hover, #NewNotebookBtn:hover {{
    background-color: {p['accent_hover']};
    border: none;
    border-radius: 10px;
}}

QPushButton#HeaderAddBtn, QPushButton#EmptyTrashBtn {{
    background-color: {p['accent_color']};
    color: white;
    border: 1px solid {p['accent_color']};
    border-radius: 18px !important;
    padding: 6px 16px;
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

/* Section Headers & Dividers */
QLabel.SidebarSectionHeader {{
    color: #71717A;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    background: transparent;
    padding: 10px 12px 2px 12px;
}}

QFrame.SidebarDivider {{
    background-color: #27272A;
    border: none;
    min-height: 1px;
    max-height: 1px;
    margin: 4px 0px;
}}

/* Mini Add Buttons inside rows (+ buttons, 32x32 rounded squares) */
QPushButton.SidebarMiniAddBtn {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_muted']};
    font-size: 18px;
    font-weight: 500;
    padding: 0px 0px 2px 0px;
    margin: 0px;
}}
QPushButton.SidebarMiniAddBtn:hover {{
    background-color: {p['card_hover']};
    border-color: {p['border_focus']};
    color: {p['text_main']};
}}
QPushButton.SidebarMiniAddBtn[parent_active="true"] {{
    background-color: {p['card_selected']};
    border-color: {p['border_focus']};
    color: {p['text_main']};
}}
QPushButton.SidebarMiniAddBtn[parent_active="true"]:hover {{
    background-color: {p.get('card_selected_hover', p['accent_hover'])};
    border-color: {p['border_focus']};
    color: {p['text_main']};
}}

/* Sidebar Standard Buttons: Home, Agenda, All Notes, Notebooks, Trash, Settings, Models, Workflows */
#HomeBtn, #AgendaBtn, #AllNotesBtn, #NotebooksHeaderBtn, #TrashBtn, #SettingsBtn, #ModelsHeaderBtn, #LibHeaderBtn {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {p['text_main']};
    text-align: left;
    border-radius: 8px;
    padding: 0px;
    margin: 0px;
}}

#HomeBtn QLabel, #AgendaBtn QLabel, #AllNotesBtn QLabel, #NotebooksHeaderBtn QLabel, #TrashBtn QLabel, #SettingsBtn QLabel, #ModelsHeaderBtn QLabel, #LibHeaderBtn QLabel {{
    color: {p['text_main']};
    font-size: 14px;
    font-weight: 600;
    background: transparent;
}}

#HomeBtn:hover, #AgendaBtn:hover, #AllNotesBtn:hover, #NotebooksHeaderBtn:hover, #TrashBtn:hover, #SettingsBtn:hover, #ModelsHeaderBtn:hover, #LibHeaderBtn:hover {{
    background-color: {p['card_hover']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
}}

#HomeBtn:hover QLabel, #AgendaBtn:hover QLabel, #AllNotesBtn:hover QLabel, #NotebooksHeaderBtn:hover QLabel, #TrashBtn:hover QLabel, #SettingsBtn:hover QLabel, #ModelsHeaderBtn:hover QLabel, #LibHeaderBtn:hover QLabel {{
    color: {p['text_main']};
}}

#HomeBtn:pressed, #AgendaBtn:pressed, #AllNotesBtn:pressed, #NotebooksHeaderBtn:pressed, #TrashBtn:pressed, #SettingsBtn:pressed, #ModelsHeaderBtn:pressed, #LibHeaderBtn:pressed {{
    background-color: {p['border_color']};
    border: 1px solid {p['border_focus']};
    border-radius: 8px;
}}

#HomeBtn:pressed QLabel, #AgendaBtn:pressed QLabel, #AllNotesBtn:pressed QLabel, #NotebooksHeaderBtn:pressed QLabel, #TrashBtn:pressed QLabel, #SettingsBtn:pressed QLabel, #ModelsHeaderBtn:pressed QLabel, #LibHeaderBtn:pressed QLabel {{
    color: {p['text_main']};
}}

/* Clean rounded pill active indicator */
#HomeBtn[active="true"], #AgendaBtn[active="true"], #AllNotesBtn[active="true"], #NotebooksHeaderBtn[active="true"],
#TrashBtn[active="true"], #SettingsBtn[active="true"],
#ModelsHeaderBtn[active="true"], #LibHeaderBtn[active="true"] {{
    background-color: {p['card_selected']};
    border: 1px solid {p['border_focus']};
    border-radius: 8px;
}}

#HomeBtn[active="true"] QLabel, #AgendaBtn[active="true"] QLabel, #AllNotesBtn[active="true"] QLabel, #NotebooksHeaderBtn[active="true"] QLabel,
#TrashBtn[active="true"] QLabel, #SettingsBtn[active="true"] QLabel,
#ModelsHeaderBtn[active="true"] QLabel, #LibHeaderBtn[active="true"] QLabel {{
    color: {p['text_main']};
    font-weight: 600;
}}

/* Special Outlined Button for İş Akışı Oluşturucu (Workflow Builder) */
#WorkflowBuilderBtn {{
    background-color: transparent;
    border: 1.5px solid #48484E;
    border-radius: 10px;
    color: #FFFFFF;
    text-align: left;
    padding: 0px;
    margin: 0px;
}}
#WorkflowBuilderBtn QLabel {{
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
    background: transparent;
}}
#WorkflowBuilderBtn:hover {{
    background-color: #222226;
    border: 1.5px solid #606066;
}}
#WorkflowBuilderBtn:hover QLabel {{
    color: #FFFFFF;
}}
#WorkflowBuilderBtn:pressed {{
    background-color: #2A2A2E;
    border: 1.5px solid #71717A;
}}
#WorkflowBuilderBtn[active="true"] {{
    background-color: #28282A;
    border: 1.5px solid #71717A;
}}
#WorkflowBuilderBtn[active="true"] QLabel {{
    color: #FFFFFF;
    font-weight: 600;
}}

/* Sidebar Collapse Toggle Button */
#SidebarCollapseBtn {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 0px;
    margin: 0px;
}}
#SidebarCollapseBtn:hover {{
    background-color: {p['bg_input']};
    border: 1px solid transparent;
    border-radius: 10px;
}}
#SidebarCollapseBtn:pressed {{
    background-color: {p['border_color']};
    border-radius: 10px;
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

/* List Widgets for Sidebar list items (Models, Notebooks, Workflow Libs) */
#ModelsList, #NotebooksList, #LibrariesList, QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}
#ModelsList::item, #NotebooksList::item, #LibrariesList::item, QListWidget::item {{
    background-color: transparent;
    color: #8E8E93;
    padding: 4px 8px;
    min-height: 24px;
    border-radius: 6px;
    margin-bottom: 2px;
}}
#ModelsList::item:hover, #NotebooksList::item:hover, #LibrariesList::item:hover, QListWidget::item:hover {{
    background-color: #222224;
    color: #FFFFFF;
}}
#ModelsList::item:selected, #NotebooksList::item:selected, #LibrariesList::item:selected, QListWidget::item:selected {{
    background-color: #28282A;
    color: #FFFFFF;
    font-weight: 500;
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
    background-color: {p.get('badge_bg', p['bg_input'])};
    border: 1px solid {p['border_color']};
    border-radius: 4px;
    color: {p['text_main']};
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
    color: {p['text_muted']};
    font-size: 18px;
    font-weight: bold;
    padding: 0px;
    margin: 0px;
}}
QPushButton#CardFavBtn:hover {{
    color: {p['highlight_color']};
}}
QPushButton#CardFavBtn[favorite="true"] {{
    color: {p['highlight_color']};
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

#DetailPanelWidget QLineEdit, 
#DetailPanelWidget QTextEdit, 
#DetailPanelWidget QPlainTextEdit,
#DetailPanelWidget QComboBox {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_main']};
    padding: 6px;
    font-size: 12px;
}}

#DetailPanelWidget QLineEdit:focus, 
#DetailPanelWidget QTextEdit:focus, 
#DetailPanelWidget QPlainTextEdit:focus,
#DetailPanelWidget QComboBox:focus {{
    border: 1px solid {p['border_focus']};
}}

#DetailPanelWidget QComboBox::drop-down {{
    border: none;
}}

QLineEdit#NoteTitleEdit {{
    font-size: 18px;
    font-weight: bold;
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_main']};
    padding: 8px 10px;
}}
QLineEdit#NoteTitleEdit:focus {{
    border: 1px solid {p['border_focus']};
}}

#WorkflowPromptEdit {{
    background-color: {p['bg_main']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_main']};
    font-size: 11px;
    padding: 6px;
}}

QLabel#WorkflowNodePill {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 500;
}}

QPushButton#WorkflowModelPill {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}}
QPushButton#WorkflowModelPill:hover {{
    background-color: {p['accent_light']};
    border-color: {p['border_focus']};
    color: {p['text_light']};
}}

QLabel#WorkflowParamBadge {{
    background-color: {p['bg_input']};
    color: {p['text_muted']};
    border: 1px solid {p['border_color']};
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
}}

QLabel#WorkflowArchBadge {{
    background-color: {p['accent_light']};
    color: {p['text_light']};
    border: 1px solid {p['border_focus']};
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}}

QWidget#WorkflowSeedCard {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
}}

#SeedTitleLabel {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: bold;
}}

#SeedValueLabel {{
    color: {p['text_main']};
    font-size: 12px;
    font-family: monospace;
    font-weight: bold;
}}

QPushButton#DetailSubBtn {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}}
QPushButton#DetailSubBtn:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
    color: {p['text_main']};
}}

QPushButton#DetailSubBtnNeg {{
    background-color: {p['bg_input']};
    color: #F28B82;
    border: 1px solid {p['border_color']};
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}}
QPushButton#DetailSubBtnNeg:hover {{
    background-color: {p['border_color']};
    border-color: #F28B82;
    color: #F28B82;
}}

QPushButton#CopyClipBtn {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#CopyClipBtn:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
}}

QLabel#DetailImageLabel {{
    background-color: {p['card_img_bg']};
    border-radius: 8px;
    color: {p['text_muted']};
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


/* Global Context Menus */
QMenu {{
    background-color: {p['bg_card']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    background-color: transparent;
    color: {p['text_main']};
    padding: 6px 14px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {p['card_hover']};
    color: {p['text_main']};
}}
QMenu::separator {{
    height: 1px;
    background-color: {p['border_color']};
    margin: 4px 8px;
}}

/* Global ToolTip */
QToolTip {{
    background-color: {p['bg_input']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* Notebook Badges */
#NotebookCardBadge, #NotebooksBadge {{
    background-color: {p.get('badge_bg', p.get('bg_input', '#282A2E'))};
    color: {p.get('text_main', '#C2E7FF')};
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
}}

/* Card Action Overlay Buttons */
QPushButton#CardCopyTriggersBtn {{
    background-color: {p.get('bg_input', '#282A2E')};
    border: 1px solid {p.get('border_color', '#3A3A3C')};
    border-radius: 13px;
    color: {p.get('highlight_color', '#C2E7FF')};
    font-size: 11px;
    padding: 0px;
}}
QPushButton#CardCopyTriggersBtn:hover {{
    background-color: {p.get('card_hover', '#38383D')};
    border-color: {p.get('border_focus', '#8AB4F8')};
    color: {p.get('text_main', '#FFFFFF')};
}}

QLabel#CardHiddenBadge {{
    background-color: {p.get('bg_input', '#282A2E')};
    border: 1px solid {p.get('border_color', '#3A3A3C')};
    border-radius: 14px;
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

/* Workflow Builder Comprehensive Styling */
#WorkflowBuilderDialog, #WorkflowBuilderViewWidget {{
    background-color: {p['bg_main']};
}}

.WorkflowBuilderCard, #WorkflowBuilderCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}

#SectionHeaderLabel {{
    color: {p['text_main']};
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 0.2px;
}}

#SubSectionLabel {{
    color: {p['text_main']};
    font-size: 12px;
    font-weight: 600;
}}

#FieldLabel {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: 500;
}}

/* Modern SpinBox & ComfyUI Stepper */
#ModernSpinBox, #ComfySpinBox {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 5px;
    min-height: 26px;
    max-height: 30px;
}}

#ModernSpinBox:focus-within, #ComfySpinBox:focus-within {{
    border-color: {p['border_focus']};
}}

#ModernSpinEdit, #ComfySpinEdit {{
    background: transparent;
    border: none;
    color: {p['text_main']};
    font-size: 11px;
    font-weight: 600;
    padding: 1px 4px;
}}

QPushButton.ModernSpinBtn {{
    background-color: transparent;
    border: none;
    color: {p['text_muted']};
    font-size: 8px;
    font-weight: bold;
    min-width: 16px;
    max-width: 16px;
    min-height: 12px;
    max-height: 12px;
    padding: 0px;
}}

QPushButton.ModernSpinBtn:hover {{
    background-color: rgba(255, 255, 255, 0.1);
    color: {p['text_main']};
    border-radius: 2px;
}}

/* Dashed Input Drop Area */
#ModernDropArea {{
    background-color: {p['bg_input']};
    border: 1px dashed {p['border_color']};
    border-radius: 8px;
    min-height: 72px;
    max-height: 78px;
    padding: 6px;
}}

#ModernDropArea:hover, #ModernDropArea[active="true"] {{
    border-color: {p['border_focus']};
    background-color: {p['accent_light']};
}}

/* Canli Onizleme Semasi Card */
#SchemaCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
    min-height: 64px;
}}

.SchemaPill {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 6px;
    padding: 4px 10px;
    color: {p['text_main']};
    font-size: 11px;
    font-weight: 600;
}}

.SchemaPill[active="true"] {{
    border-color: {p['border_focus']};
    color: {p['border_focus']};
}}

#SchemaArrow {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: bold;
}}

.BuilderCard, #BuilderCard, #ModelCard, #PromptCard, #KSamplerCard, #ResolutionCard, .ComfyNodeCard, #ComfyNodeCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}

.BuilderCard:hover, .ComfyNodeCard:hover {{
    border-color: {p['border_focus']};
}}

.ComfyNodeHeader {{
    border-bottom: 1px solid {p['border_color']};
    padding: 6px 12px;
    background-color: {p['bg_input']};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

.ComfyDot {{
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
    background-color: {p['border_focus']};
}}

.ComfyDot[color="green"] {{
    background-color: #10B981;
}}

.ComfyDot[color="red"] {{
    background-color: #EF4444;
}}

.ComfyDot[color="orange"] {{
    background-color: #F59E0B;
}}

.ComfyDot[color="purple"] {{
    background-color: #8B5CF6;
}}

.ComfyDot[color="blue"] {{
    background-color: #0EA5E9;
}}

#BuilderCardHeader {{
    color: {p['text_main']};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}

#BuilderBadge {{
    background-color: {p['accent_light']};
    color: {p['border_focus']};
    border: 1px solid {p['border_focus']};
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 9px;
    font-weight: 700;
}}

#ComfyStepperLabel {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: 600;
}}

/* ComfyUI Stepper Capsules [ < label ... value > ] */
.ComfyStepper {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 6px;
    min-height: 28px;
}}

.ComfyStepper:hover {{
    border-color: {p['border_focus']};
}}

QPushButton.ComfyStepBtn {{
    background-color: transparent;
    border: none;
    color: {p['text_muted']};
    font-weight: bold;
    font-size: 11px;
    min-width: 20px;
    max-width: 20px;
    min-height: 24px;
    padding: 0px;
}}

QPushButton.ComfyStepBtn:hover {{
    background-color: rgba(255, 255, 255, 0.08);
    color: {p['text_main']};
    border-radius: 4px;
}}

QPushButton.ComfyStepBtn:pressed {{
    background-color: {p['accent_color']};
    color: #FFFFFF;
}}

QLineEdit.ComfyValEdit {{
    background: transparent;
    border: none;
    color: {p['text_main']};
    font-size: 12px;
    font-weight: bold;
    padding: 2px 4px;
}}

/* Compact Image Slot */
#CompactDropArea {{
    background-color: {p['bg_input']};
    border: 1px dashed {p['border_color']};
    border-radius: 8px;
    min-height: 52px;
    max-height: 58px;
    padding: 4px 8px;
}}

#CompactDropArea:hover, #CompactDropArea[active="true"] {{
    border-color: {p['border_focus']};
    background-color: {p['accent_light']};
}}

/* Mode Segmented Toggle Buttons */
#ModeToggleContainer {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 10px;
    padding: 3px;
}}

QPushButton.ModeToggleBtn, QPushButton#ModeTxtBtn, QPushButton#ModeImgBtn {{
    background-color: transparent;
    color: {p['text_muted']};
    border: none;
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton.ModeToggleBtn:hover, QPushButton#ModeTxtBtn:hover, QPushButton#ModeImgBtn:hover {{
    color: {p['text_main']};
    background-color: {p['bg_card']};
}}

QPushButton.ModeToggleBtn[active="true"], QPushButton#ModeTxtBtn[active="true"], QPushButton#ModeImgBtn[active="true"] {{
    background-color: {p['accent_color']};
    color: #FFFFFF;
}}

/* Image Drop Area */
#ImageDropArea {{
    background-color: {p['bg_input']};
    border: 2px dashed {p['border_color']};
    border-radius: 12px;
}}

#ImageDropArea:hover, #ImageDropArea[active="true"] {{
    border-color: {p['border_focus']};
    background-color: {p['accent_light']};
}}

/* Form Input Styling & Row Containers */
.BuilderLabel {{
    color: {p['text_main']};
    font-size: 12px;
    font-weight: 600;
}}

.BuilderMutedLabel {{
    color: {p['text_muted']};
    font-size: 11px;
}}

/* Seed Box Container */
#SeedContainer {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    padding: 2px 6px;
}}

#SeedContainer:focus-within {{
    border: 1px solid {p['border_focus']};
}}

#SeedEdit {{
    background: transparent;
    border: none;
    color: {p['text_main']};
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 6px;
}}

#SeedRandomBtn {{
    background-color: {p['bg_card']};
    color: {p['text_main']};
    border: 1px solid {p['border_color']};
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
}}

#SeedRandomBtn:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
}}

/* LoRA Item Row */
.LoraRow {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    padding: 6px 10px;
}}

.LoraRow:hover {{
    border-color: {p['border_focus']};
}}

#AddLoraBtn {{
    background-color: {p['bg_input']};
    color: {p['border_focus']};
    border: 1px dashed {p['border_focus']};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 600;
}}

#AddLoraBtn:hover {{
    background-color: {p['accent_light']};
    border-style: solid;
}}

#RemoveLoraBtn {{
    background-color: transparent;
    color: {p['text_muted']};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 8px;
}}

#RemoveLoraBtn:hover {{
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444;
    border-color: #EF4444;
}}

/* Prompt Editors */
#PositivePromptEdit, #NegativePromptEdit {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    border-radius: 8px;
    color: {p['text_main']};
    padding: 8px;
    font-size: 12px;
}}

#PositivePromptEdit:focus {{
    border: 1px solid {p['border_focus']};
}}

#NegativePromptEdit:focus {{
    border: 1px solid #F87171;
}}

/* Bottom Action Bar */
#BuilderFooterBar {{
    background-color: {p['bg_card']};
    border-top: 1px solid {p['border_color']};
    padding: 6px 18px;
}}

#BuilderStatusLabel {{
    color: {p.get('highlight_color', p.get('border_focus', '#8AB4F8'))};
    font-size: 12px;
    font-weight: 500;
}}

#ExportJsonBtn {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_color']};
    color: {p['text_main']};
    border-radius: 6px;
    padding: 0px 14px;
    font-weight: 600;
    font-size: 12px;
}}

#ExportJsonBtn:hover {{
    background-color: {p['border_color']};
    border-color: {p['border_focus']};
}}

#ExportPngBtn {{
    background-color: {p['accent_color']};
    border: none;
    color: {'#000000' if is_light(p['accent_color']) else '#FFFFFF'};
    border-radius: 6px;
    padding: 0px 14px;
    font-weight: bold;
    font-size: 12px;
}}

#ExportPngBtn:hover {{
    background-color: {p['accent_hover']};
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

#AllNotesBadge, #NotebooksBadge, #TrashBadge, #WorkflowsBadge {{
    background-color: #232326;
    color: #A1A1AA;
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
    border: none;
    padding: 2px 8px;
    min-width: 18px;
    text-align: center;
}}

/* Notebook Overview Cards */
#NotebookCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}
#NotebookCard:hover {{
    border: 1px solid {p['border_focus']};
    background-color: {p['bg_input']};
}}
#NotebookCard[selected="true"] {{
    background-color: {p['card_selected']};
    border: 2px solid {p['highlight_color']};
    border-radius: 12px;
}}
#NotebookCard QPushButton#CardActionBtn {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
}}
#NotebookCard QPushButton#CardActionBtn:hover {{
    background-color: {p['border_color']};
    border: 1px solid {p['border_focus']};
}}
#NotebookCard QPushButton#CardDeleteBtn {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0px;
}}
#NotebookCard QPushButton#CardDeleteBtn:hover {{
    background-color: rgba(183, 28, 28, 0.4);
    border: 1px solid #F28B82;
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
    w_color = custom_colors.get("cal_weekend_color") or custom_colors.get("cal_weekend_header") or custom_colors.get("cal_weekend_text") or "#FB7185"

    return {
        # Cell backgrounds
        "cell_bg_normal": "transparent",
        "cell_bg_other_month": "transparent",
        "cell_bg_hover": p.get("card_hover", "#25272C"),
        "cell_bg_today": "transparent",
        
        # Selection
        "selection_bg": p.get("accent_color", "#1A73E8"),
        "selection_border": p.get("highlight_color", p.get("border_focus", "#8AB4F8")),
        "selection_text": "#FFFFFF",
        
        # Today
        "today_border": p.get("highlight_color", p.get("border_focus", "#8AB4F8")),
        
        # Day texts
        "text_weekday": p.get("text_main", "#E3E3E3"),
        "text_weekend": w_color,       # User-customizable weekend day numbers!
        "text_other_month": adjust_brightness(p.get("text_muted", "#9AA0A6"), 0.5),
        
        # Column headers
        "header_weekday": p.get("text_muted", "#9AA0A6"),
        "header_weekend": w_color,   # User-customizable weekend headers!
        
        # Status Dots
        "dot_pending_tasks": "#F59E0B",    # Amber
        "dot_completed_tasks": "#10B981",  # Emerald Green
        "dot_daily_note": "#38BDF8",       # Light Sky Blue
        
        # General palette reference
        "palette": p
    }

STYLE_SHEET = get_stylesheet("Koyu Gece")
