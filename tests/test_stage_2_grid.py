import sys
import os

# Set offscreen platform before creating QApplication
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add workspace to sys.path
workspace_dir = r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote"
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize, QPoint, QRect
from PySide6.QtGui import QImage, QPixmap

from ui.library_view import LibraryView, ModelCardWidget
from ui.notes_view import NotesView, NoteCardWidget
from ui.workflow_view import WorkflowView, WorkflowCardWidget
from utils.cache import THUMBNAIL_CACHE

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    # 1. Create dummy image files for testing thumbnail loading
    dummy_img_dir = os.path.join(workspace_dir, "scratch")
    os.makedirs(dummy_img_dir, exist_ok=True)
    created_dummy_files = []
    def get_dummy_img(idx):
        p = os.path.join(dummy_img_dir, f"test_thumb_{idx}.png")
        if not os.path.exists(p):
            img = QImage(300, 300, QImage.Format_RGB32)
            img.fill(0xFF445566)
            img.save(p)
            created_dummy_files.append(p)
        return p

    print("[1/3] Testing LibraryView...")
    lib_view = LibraryView()
    lib_view.resize(800, 600)
    lib_view.show()
    
    # 60 mock models
    mock_models = [
        {
            'id': i,
            'name': f"Model_{i}",
            'file_path': f"C:/models/model_{i}.safetensors",
            'image_path': get_dummy_img(f"model_{i}") if (i % 2 == 0) else None,
            'is_favorite': 0,
            'is_hidden': 0
        }
        for i in range(60)
    ]
    lib_view.set_library("Lora Modelleri", mock_models)
    
    # Process any pending events
    if getattr(lib_view, 'loading_timer', None):
        while lib_view.loading_timer.isActive():
            app.processEvents()
    else:
        app.processEvents()
        
    assert len(lib_view.cards) == 60, f"Expected 60 cards, got {len(lib_view.cards)}"
    assert lib_view.current_columns > 0, f"Expected current_columns > 0, got {lib_view.current_columns}"
    print(f"  [OK] 60 cards populated, current_columns = {lib_view.current_columns}")
    
    # Check card 54
    card_54 = lib_view.cards[54]
    assert isinstance(card_54, ModelCardWidget)
    print("  [OK] Card 54 created and verified")
    
    # Check column caching during resize
    old_cols = lib_view.current_columns
    lib_view.resize(lib_view.width() + 10, lib_view.height()) # slight change, column shouldn't change
    app.processEvents()
    assert lib_view.current_columns == old_cols, "Columns should not change on minor width delta"
    print("  [OK] Column caching on minor resize verified")
    
    # Check check_visible_cards works without errors
    lib_view.check_visible_cards()
    print("  [OK] check_visible_cards executed cleanly")
    
    # Clear cache before notes test so we test uncached deferred loading
    THUMBNAIL_CACHE.clear()

    print("[2/3] Testing NotesView...")
    notes_view = NotesView()
    notes_view.resize(800, 600)
    notes_view.show()
    
    mock_notes = [
        {
            'id': i,
            'title': f"Note_{i}",
            'content': f"<p>Content for note {i}</p>",
            'display_mode': 'WITH_IMAGE' if (i % 2 == 0) else 'TEXT_ONLY',
            'image_path': get_dummy_img(f"note_{i}") if (i % 2 == 0) else None,
            'is_favorite': 0,
            'is_pinned_corkboard': 0,
            'color_hex': 'default'
        }
        for i in range(60)
    ]
    notes_view.set_notes(mock_notes)
    
    if getattr(notes_view, 'loading_timer', None):
        while notes_view.loading_timer.isActive():
            app.processEvents()
    else:
        app.processEvents()
        
    assert len(notes_view.cards) == 60, f"Expected 60 note cards, got {len(notes_view.cards)}"
    assert notes_view.current_columns > 0, f"Expected current_columns > 0, got {notes_view.current_columns}"
    print(f"  [OK] 60 notes populated, current_columns = {notes_view.current_columns}")
    
    note_54 = notes_view.cards[54] # even index -> WITH_IMAGE
    assert isinstance(note_54, NoteCardWidget)
    print("  [OK] Note card 54 created and verified")
    
    # Text-only note should be marked image_loaded == True immediately
    note_55 = notes_view.cards[55] # odd index -> TEXT_ONLY
    assert isinstance(note_55, NoteCardWidget)
    assert note_55.image_loaded is True, "Text-only note should have image_loaded == True"
    print("  [OK] Text-only note card immediately marked loaded")
    
    # Test ensure_image_loaded
    note_54.ensure_image_loaded()
    assert note_54.image_loading is True or note_54.image_loaded is True
    print("  [OK] Note ensure_image_loaded triggered cleanly")
    
    # Test prepare_for_deletion
    note_54.prepare_for_deletion()
    assert note_54.image_label.pixmap().isNull()
    print("  [OK] Note prepare_for_deletion cleans up QPixmap")

    # Clear cache before workflow test
    THUMBNAIL_CACHE.clear()

    print("[3/3] Testing WorkflowView...")
    wf_view = WorkflowView()
    wf_view.resize(800, 600)
    wf_view.show()
    
    mock_wfs = [
        {
            'id': i,
            'name': f"Workflow_{i}",
            'file_path': f"C:/workflows/wf_{i}.json",
            'description': f"Description {i}",
            'image_path': get_dummy_img(f"wf_{i}") if (i % 2 == 0) else None,
            'is_favorite': 0,
            'is_hidden': 0
        }
        for i in range(60)
    ]
    wf_view.set_workflows(1, "Workflows", mock_wfs)
    
    if getattr(wf_view, 'loading_timer', None):
        while wf_view.loading_timer.isActive():
            app.processEvents()
    else:
        app.processEvents()
        
    assert len(wf_view.cards) == 60, f"Expected 60 workflow cards, got {len(wf_view.cards)}"
    assert wf_view.current_columns > 0, f"Expected current_columns > 0, got {wf_view.current_columns}"
    print(f"  [OK] 60 workflows populated, current_columns = {wf_view.current_columns}")
    
    wf_54 = wf_view.cards[54]
    assert isinstance(wf_54, WorkflowCardWidget)
    print("  [OK] Workflow card 54 verified")
    
    wf_54.ensure_image_loaded()
    assert wf_54.image_loading is True or wf_54.image_loaded is True
    print("  [OK] Workflow ensure_image_loaded triggered cleanly")
    
    wf_54.prepare_for_deletion()
    assert wf_54.image_label.pixmap().isNull()
    print("  [OK] Workflow prepare_for_deletion cleans up QPixmap")
    
    # Cleanup all dummy images
    for f in created_dummy_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
        
    print("\nALL STAGE 2 TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    run_tests()
