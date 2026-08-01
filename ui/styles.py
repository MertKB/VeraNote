# ui/styles.py
import json

PALETTES = {
    "Koyu Gece": {
        "bg_main": "#131314",
        "bg_card": "#1E1F20",
        "bg_input": "#2D2F31",
        "border_color": "#2F2F2F",
        "border_focus": "#8AB4F8",
        "accent_color": "#1A73E8",
        "accent_hover": "#1557B0",
        "accent_light": "#004A77",
        "text_main": "#E3E3E3",
        "text_muted": "#9AA0A6",
        "text_light": "#C2E7FF"
    },
    "Derin Mor": {
        "bg_main": "#120E16",
        "bg_card": "#1D1625",
        "bg_input": "#2D2237",
        "border_color": "#30223A",
        "border_focus": "#D7AEF5",
        "accent_color": "#A061D8",
        "accent_hover": "#8049B6",
        "accent_light": "#432B5B",
        "text_main": "#EAE5ED",
        "text_muted": "#B5A9BC",
        "text_light": "#F0E4FF"
    },
    "Okyanus Mavisi": {
        "bg_main": "#06131D",
        "bg_card": "#0C2030",
        "bg_input": "#132D42",
        "border_color": "#18374E",
        "border_focus": "#00E5FF",
        "accent_color": "#00B0FF",
        "accent_hover": "#0091EA",
        "accent_light": "#00365C",
        "text_main": "#E0F2F1",
        "text_muted": "#80CBC4",
        "text_light": "#E0F7FA"
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

def get_stylesheet(theme_name="Koyu Gece", custom_colors=None):
    if theme_name in ["Özel Tema", "Custom"]:
        if isinstance(custom_colors, str):
            try:
                custom_colors = json.loads(custom_colors)
            except Exception:
                custom_colors = None
        if not isinstance(custom_colors, dict):
            custom_colors = {}
            
        bg_main = custom_colors.get("bg_main", "#131314")
        bg_card = custom_colors.get("bg_card", "#1E1F20")
        accent_color = custom_colors.get("accent_color", "#1A73E8")
        
        # Derive auxiliary theme colors dynamically
        bg_input = adjust_brightness(bg_card, 1.2)
        border_color = adjust_brightness(bg_card, 1.4)
        border_focus = adjust_brightness(accent_color, 1.2)
        accent_hover = adjust_brightness(accent_color, 0.8)
        accent_light = adjust_brightness(accent_color, 0.3)
        text_light = adjust_brightness(accent_color, 1.5)
        
        p = {
            "bg_main": bg_main,
            "bg_card": bg_card,
            "bg_input": bg_input,
            "border_color": border_color,
            "border_focus": border_focus,
            "accent_color": accent_color,
            "accent_hover": accent_hover,
            "accent_light": accent_light,
            "text_main": "#E3E3E3",
            "text_muted": "#9AA0A6",
            "text_light": text_light
        }
    else:
        p = PALETTES.get(theme_name, PALETTES["Koyu Gece"])
        
    return f"""
QMainWindow {{
    background-color: {p['bg_main']};
    color: {p['text_main']};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

/* ScrollBar Styling */
QScrollBar:vertical {{
    border: none;
    background: {p['bg_card']};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {p['border_color']};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['border_focus']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: {p['bg_card']};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {p['border_color']};
    min-width: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {p['border_focus']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
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
    background-color: {p['bg_card']};
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
#HomeBtn, #AllNotesBtn, #TrashBtn, #SettingsBtn {{
    background-color: transparent;
    border: none;
    color: {p['text_main']};
    text-align: left;
    border-radius: 10px;
    transition: background-color 0.2s ease, color 0.2s ease;
}}

#HomeBtn QLabel, #AllNotesBtn QLabel, #TrashBtn QLabel, #SettingsBtn QLabel {{
    color: {p['text_main']};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
    transition: color 0.2s ease;
}}

#HomeBtn:hover, #AllNotesBtn:hover, #TrashBtn:hover, #SettingsBtn:hover {{
    background-color: {p['bg_input']};
    color: white;
}}

#HomeBtn:hover QLabel, #AllNotesBtn:hover QLabel, #TrashBtn:hover QLabel, #SettingsBtn:hover QLabel {{
    color: white;
}}

#HomeBtn:pressed, #AllNotesBtn:pressed, #TrashBtn:pressed, #SettingsBtn:pressed {{
    background-color: {p['border_color']};
    color: white;
}}

#HomeBtn:pressed QLabel, #AllNotesBtn:pressed QLabel, #TrashBtn:pressed QLabel, #SettingsBtn:pressed QLabel {{
    color: white;
}}

#HomeBtn[active="true"], #AllNotesBtn[active="true"], #TrashBtn[active="true"], #SettingsBtn[active="true"] {{
    background-color: {p['accent_light']};
    border-left: 4px solid {p['border_focus']};
    border-radius: 8px;
}}

#HomeBtn[active="true"] QLabel, #AllNotesBtn[active="true"] QLabel, #TrashBtn[active="true"] QLabel, #SettingsBtn[active="true"] QLabel {{
    color: {p['text_light']};
    font-weight: bold;
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

/* Model Card */
#ModelCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border_color']};
    border-radius: 12px;
}}
#ModelCard:hover {{
    border: 1px solid {p['border_focus']};
    background-color: {p['bg_input']};
}}

#CardTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {p['text_main']};
}}

#CardFilename {{
    font-size: 11px;
    color: {p['text_muted']};
}}

#CardImageLabel {{
    background-color: {p['bg_main']};
    border-top-left-radius: 11px;
    border-top-right-radius: 11px;
}}

/* Detail Panel */
#DetailPanelWidget {{
    background-color: {p['bg_card']};
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
    background-color: {p['accent_light']};
    border-color: {p['accent_light']};
    color: {p['text_light']};
}}
#FavToggleBtn:checked:hover {{
    background-color: {p['accent_hover']};
    color: white;
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
    background-color: {p['bg_main']};
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
"""

STYLE_SHEET = get_stylesheet("Koyu Gece")
