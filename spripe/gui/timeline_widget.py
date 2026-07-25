import os
import subprocess
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
                             QPushButton, QLabel, QMessageBox, QStackedWidget, QGraphicsOpacityEffect)
from PyQt6.QtGui import QIcon, QPixmap, QImage
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QThread, QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve

class CustomListWidget(QListWidget):
    order_changed = pyqtSignal()
    delete_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(100, 100))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(10)
        
        # Enable multiple selection
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
    def dropEvent(self, event):
        if event.source() == self:
            drop_pos = event.position().toPoint()
            target_item = self.itemAt(drop_pos)
            target_row = self.row(target_item) if target_item else self.count()
            
            selected_items = self.selectedItems()
            if not selected_items: 
                event.ignore()
                return
                
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        
        selected_rows = sorted([self.row(item) for item in selected_items])
        
        # Calculate target index after removals
        adjusted_target = target_row
        for row in selected_rows:
            if row < target_row:
                adjusted_target -= 1
                
        # Remove items from highest index to lowest to avoid shifting issues
        items_to_move = []
        for row in reversed(selected_rows):
            items_to_move.append(self.takeItem(row))
            
        items_to_move.reverse()
        
        # Insert them back at the calculated index
        for i, item in enumerate(items_to_move):
            self.insertItem(adjusted_target + i, item)
            item.setSelected(True)
            
        self.order_changed.emit()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)

class FrameLoaderThread(QThread):
    frames_loaded = pyqtSignal(list)
    
    def __init__(self, folder, files):
        super().__init__()
        self.folder = folder
        self.files = files
        
    def run(self):
        result = []
        for f in self.files:
            file_path = os.path.join(self.folder, f)
            # Load as QImage which is thread-safe (QPixmap is not)
            img = QImage(file_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
            result.append((f, file_path, img))
        self.frames_loaded.emit(result)


class TimelineWidget(QWidget):
    frame_selected = pyqtSignal(str)
    pinned_keyframe_updated = pyqtSignal(str) # Path to pinned frame or empty string
    
    def __init__(self, base_dir, settings_manager, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.settings_manager = settings_manager
        self.current_asset = None
        self.current_asset_path = None
        self.current_folder = None
        self.icon_dir = os.path.join(os.path.dirname(__file__), "icons")
        
        # Animation Player State
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_frame)
        self.frames = []
        self.current_frame_idx = 0
        self.is_playing = False
        self.is_looping = self.settings_manager.get("play_loop_default", True)
        self.is_boomerang = self.settings_manager.get("play_boomerang_default", False)
        self.play_direction = 1
        
        self.init_ui()
        
    def get_icon(self, name):
        return QIcon(os.path.join(self.icon_dir, f"{name}.svg"))
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setStyleSheet("""
            QPushButton:checked {
                background-color: #0078D7;
                border: 1px solid #55AAFF;
                border-radius: 4px;
            }
        """)
        
        # --- Timeline Header ---
        header_layout = QHBoxLayout()
        self.label = QLabel("Timeline")
        self.label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(self.label)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(self.get_icon("delete"))
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_delete.setEnabled(False)
        header_layout.addWidget(self.btn_delete)
        
        self.btn_reverse = QPushButton("Reverse")
        self.btn_reverse.setIcon(self.get_icon("reverse"))
        self.btn_reverse.clicked.connect(self.reverse_sequence)
        self.btn_reverse.setEnabled(False)
        header_layout.addWidget(self.btn_reverse)
        
        # Pinned Keyframe Buttons
        self.btn_pin = QPushButton("📌 Pin")
        self.btn_pin.setToolTip("Set selected frame as pinned overlay for this asset")
        self.btn_pin.clicked.connect(self.pin_keyframe)
        self.btn_pin.setEnabled(False)
        header_layout.addWidget(self.btn_pin)
        
        self.btn_clear_pin = QPushButton("❌ Unpin")
        self.btn_clear_pin.setToolTip("Clear the pinned overlay")
        self.btn_clear_pin.clicked.connect(self.clear_pinned_keyframe)
        self.btn_clear_pin.setEnabled(False)
        header_layout.addWidget(self.btn_clear_pin)
        
        header_layout.addStretch()
        
        # --- Animation Player Controls ---
        self.player_label = QLabel("Frame: 0/0")
        header_layout.addWidget(self.player_label)
        
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.get_icon("play"))
        self.btn_play.setToolTip("Play")
        self.btn_play.clicked.connect(self.play_anim)
        header_layout.addWidget(self.btn_play)
        
        self.btn_pause = QPushButton()
        self.btn_pause.setIcon(self.get_icon("pause"))
        self.btn_pause.setToolTip("Pause")
        self.btn_pause.clicked.connect(self.pause_anim)
        header_layout.addWidget(self.btn_pause)
        
        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(self.get_icon("stop"))
        self.btn_stop.setToolTip("Stop")
        self.btn_stop.clicked.connect(self.stop_anim)
        header_layout.addWidget(self.btn_stop)
        
        self.btn_loop = QPushButton()
        self.btn_loop.setIcon(self.get_icon("loop"))
        self.btn_loop.setToolTip("Toggle Loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(self.is_looping)
        self.btn_loop.clicked.connect(self.toggle_loop)
        header_layout.addWidget(self.btn_loop)
        
        self.btn_boomerang = QPushButton()
        self.btn_boomerang.setIcon(self.get_icon("boomerang"))
        self.btn_boomerang.setToolTip("Toggle Boomerang (Ping-Pong)")
        self.btn_boomerang.setCheckable(True)
        self.btn_boomerang.setChecked(self.is_boomerang)
        self.btn_boomerang.clicked.connect(self.toggle_boomerang)
        header_layout.addWidget(self.btn_boomerang)
        
        main_layout.addLayout(header_layout)
        
        # --- Timeline Area (Stacked for Loading) ---
        self.stack = QStackedWidget()
        
        self.list_widget = CustomListWidget()
        self.list_widget.order_changed.connect(self.on_order_changed)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.list_widget.delete_requested.connect(self.delete_selected)
        
        # Loading Overlay
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        self.loading_lbl = QLabel("Loading Frames...")
        self.loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl.setStyleSheet("font-size: 18px; color: #AAAAAA; font-weight: bold;")
        
        # Create pulsing animation
        self.opacity_effect = QGraphicsOpacityEffect(self.loading_lbl)
        self.loading_lbl.setGraphicsEffect(self.opacity_effect)
        
        self.anim_group = QSequentialAnimationGroup(self)
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(600)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.2)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_in.setDuration(600)
        fade_in.setStartValue(0.2)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self.anim_group.addAnimation(fade_out)
        self.anim_group.addAnimation(fade_in)
        self.anim_group.setLoopCount(-1) # Infinite loop
        
        loading_layout.addWidget(self.loading_lbl)
        
        self.stack.addWidget(self.list_widget)
        self.stack.addWidget(self.loading_widget)
        
        main_layout.addWidget(self.stack)
        
        self.set_player_enabled(False)
        
        from spripe.core.signal_manager import SignalManager
        SignalManager.get_instance().settings_changed.connect(self.on_settings_changed)
        
    def on_settings_changed(self, key, value):
        if key == "play_loop_default":
            self.is_looping = value
            self.btn_loop.setChecked(value)
        elif key == "play_boomerang_default":
            self.is_boomerang = value
            self.btn_boomerang.setChecked(value)
        
    def load_path(self, path, name):
        if not path or not os.path.exists(path):
            self.current_folder = None
            self.label.setText("Timeline: No frames found")
            self.list_widget.clear()
            self.btn_delete.setEnabled(False)
            self.btn_reverse.setEnabled(False)
            self.btn_pin.setEnabled(False)
            self.set_player_enabled(False)
            return
            
        self.current_folder = path
        self.label.setText(f"Timeline: {name}")
        self.btn_delete.setEnabled(False)
        self.btn_reverse.setEnabled(True)
        self.set_player_enabled(True)
        self.stop_anim()
        self.refresh_timeline()        
    def load_animation(self, asset_path, anim_name):
        self.current_asset = anim_name
        self.current_asset_path = asset_path
        raw_path = os.path.join(asset_path, "raw_output", f"out_python_{anim_name}")
        norm_path = os.path.join(asset_path, "normalized_output", f"normalized_{anim_name}")
        
        if os.path.exists(norm_path) and len(os.listdir(norm_path)) > 0:
            self.current_folder = norm_path
            self.label.setText(f"Timeline: Normalized ({anim_name})")
        elif os.path.exists(raw_path) and len(os.listdir(raw_path)) > 0:
            self.current_folder = raw_path
            self.label.setText(f"Timeline: Raw ({anim_name})")
        else:
            self.current_folder = None
            self.label.setText(f"Timeline: No frames found for {anim_name}")
            self.list_widget.clear()
            self.btn_delete.setEnabled(False)
            self.btn_reverse.setEnabled(False)
            self.btn_pin.setEnabled(False)
            self.set_player_enabled(False)
            return
            
        self.btn_delete.setEnabled(False)
        self.btn_reverse.setEnabled(True)
        self.set_player_enabled(True)
        self.stop_anim()
        self.refresh_timeline()
        
    def load_asset(self, asset_name):
        # Legacy fallback
        self.current_asset_path = os.path.join(self.base_dir, "Standalone", asset_name)
        raw_path = os.path.join(self.base_dir, "raw_output", f"out_python_{asset_name}")
        norm_path = os.path.join(self.base_dir, "normalized_output", f"normalized_{asset_name}")
        
        if os.path.exists(norm_path) and len(os.listdir(norm_path)) > 0:
            self.current_folder = norm_path
            self.label.setText(f"Timeline: Normalized ({asset_name})")
        elif os.path.exists(raw_path) and len(os.listdir(raw_path)) > 0:
            self.current_folder = raw_path
            self.label.setText(f"Timeline: Raw ({asset_name})")
        else:
            self.current_folder = None
            self.label.setText("Timeline: No frames found")
            self.list_widget.clear()
            self.btn_delete.setEnabled(False)
            self.btn_reverse.setEnabled(False)
            self.btn_pin.setEnabled(False)
            self.set_player_enabled(False)
            return
            
        self.btn_delete.setEnabled(False)
        self.btn_reverse.setEnabled(True)
        self.set_player_enabled(True)
        self.stop_anim()
        self.refresh_timeline()
        
    def refresh_timeline(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.frames = []
        
        # Check pinned status
        if self.current_asset_path:
            pinned_path = os.path.join(self.current_asset_path, "pinned_keyframe.png")
            self.btn_clear_pin.setEnabled(os.path.exists(pinned_path))
        
        if not self.current_folder: 
            self.list_widget.blockSignals(False)
            return
        
        files = [f for f in os.listdir(self.current_folder) if f.endswith('.png')]
        files.sort()
        
        # Show animated loading overlay
        self.stack.setCurrentIndex(1)
        self.anim_group.start()
        
        self.loader_thread = FrameLoaderThread(self.current_folder, files)
        self.loader_thread.frames_loaded.connect(self.on_frames_loaded)
        self.loader_thread.start()
        
    def on_frames_loaded(self, result):
        self.list_widget.blockSignals(True)
        for f, file_path, img in result:
            self.frames.append(file_path)
            pixmap = QPixmap.fromImage(img)
            item = QListWidgetItem(QIcon(pixmap), f)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.list_widget.addItem(item)
            
        # Hide loading overlay and stop animation
        self.anim_group.stop()
        self.stack.setCurrentIndex(0)
            
        self.update_player_label()
        self.list_widget.blockSignals(False)
        
        # Select first item by default
        if self.list_widget.count() > 0:
            item = self.list_widget.item(0)
            item.setSelected(True)
            self.list_widget.setCurrentItem(item)
            self.current_frame_idx = 0
            
            # Delay the load by 50ms to let the UI layout finish recalculating 
            # after the QStackedWidget swap. This fixes the initial zoom glitch.
            file_path = item.data(Qt.ItemDataRole.UserRole)
            QTimer.singleShot(50, lambda path=file_path: self.frame_selected.emit(path))
            
            self.btn_delete.setEnabled(True)
            
            if self.settings_manager.get("play_autoplay_default", False):
                self.play_anim()
            
    def on_selection_changed(self):
        selected = self.list_widget.selectedItems()
        if selected:
            # Sync player index to selected item
            self.current_frame_idx = self.list_widget.row(selected[0])
            self.frame_selected.emit(selected[0].data(Qt.ItemDataRole.UserRole))
            self.btn_delete.setEnabled(True)
            self.btn_pin.setEnabled(True)
            self.update_player_label()
        else:
            self.btn_delete.setEnabled(False)
            self.btn_pin.setEnabled(False)
            
    def pin_keyframe(self):
        if not self.current_asset_path: return
        selected = self.list_widget.selectedItems()
        if not selected: return
        
        src_file = selected[0].data(Qt.ItemDataRole.UserRole)
        dest_file = os.path.join(self.current_asset_path, "pinned_keyframe.png")
        raw_dest_file = os.path.join(self.current_asset_path, "pinned_keyframe_raw.png")
        
        try:
            # 1. Copy the visual frame for the onion skin overlay
            shutil.copy2(src_file, dest_file)
            
            # 2. Find and copy the corresponding raw frame for the normalization math
            raw_src_file = src_file
            if "normalized_output" in src_file.replace('\\', '/'):
                filename = os.path.basename(src_file)
                anim_dir = os.path.basename(os.path.dirname(src_file))
                if anim_dir.startswith("normalized_"):
                    anim_name = anim_dir.removeprefix("normalized_")
                    possible_raw = os.path.join(self.current_asset_path, "raw_output", f"out_python_{anim_name}", filename)
                    if os.path.exists(possible_raw):
                        raw_src_file = possible_raw
            
            shutil.copy2(raw_src_file, raw_dest_file)
            
            self.btn_clear_pin.setEnabled(True)
            self.pinned_keyframe_updated.emit(dest_file)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pin keyframe: {e}")
            
    def clear_pinned_keyframe(self):
        if not self.current_asset_path: return
        dest_file = os.path.join(self.current_asset_path, "pinned_keyframe.png")
        raw_dest_file = os.path.join(self.current_asset_path, "pinned_keyframe_raw.png")
        if os.path.exists(dest_file):
            os.remove(dest_file)
        if os.path.exists(raw_dest_file):
            os.remove(raw_dest_file)
        self.btn_clear_pin.setEnabled(False)
        self.pinned_keyframe_updated.emit("")

    def delete_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected: return
        
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                     f"Delete {len(selected)} frames?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.stop_anim()
            for item in selected:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            if self.current_folder:
                import sys
                if self.base_dir not in sys.path:
                    sys.path.append(self.base_dir)
                from spripe.scripts.rename_frames import rename_sequence
                rename_sequence(self.current_folder)
            
            self.refresh_timeline()
            self.frame_selected.emit("")
            
    def reverse_sequence(self):
        if not self.current_folder: return
        self.stop_anim()
        import sys
        if self.base_dir not in sys.path:
            sys.path.append(self.base_dir)
        from spripe.scripts.reverse_frames import reverse_sequence
        reverse_sequence(self.current_folder)
        self.refresh_timeline()
        self.frame_selected.emit("")
        
    def on_order_changed(self):
        if not self.current_folder: return
        
        self.stop_anim()
        new_order_paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            new_order_paths.append(item.data(Qt.ItemDataRole.UserRole))
            
        temp_paths = []
        for i, old_path in enumerate(new_order_paths):
            temp_path = os.path.join(self.current_folder, f"temp_{i}.png")
            os.rename(old_path, temp_path)
            temp_paths.append(temp_path)
            
        for i, temp_path in enumerate(temp_paths):
            final_path = os.path.join(self.current_folder, f"{i:04d}.png")
            os.rename(temp_path, final_path)
            
        self.refresh_timeline()
        
    # --- Animation Player Methods ---
    def set_player_enabled(self, enabled):
        self.btn_play.setEnabled(enabled)
        self.btn_pause.setEnabled(enabled)
        self.btn_stop.setEnabled(enabled)
        self.btn_loop.setEnabled(enabled)
        self.btn_boomerang.setEnabled(enabled)
        
    def play_anim(self):
        if not self.frames: return
        self.is_playing = True
        # assuming ~12 fps for fighting game animation
        self.timer.start(83) 
        
    def pause_anim(self):
        self.is_playing = False
        self.timer.stop()
        
    def stop_anim(self):
        self.pause_anim()
        self.current_frame_idx = 0
        self.play_direction = 1
        self.update_player_selection()
        
    def toggle_loop(self):
        self.is_looping = self.btn_loop.isChecked()
        
    def toggle_boomerang(self):
        self.is_boomerang = self.btn_boomerang.isChecked()
        
    def advance_frame(self):
        if not self.frames:
            self.stop_anim()
            return
            
        self.current_frame_idx += self.play_direction
        
        if self.current_frame_idx >= len(self.frames) or self.current_frame_idx < 0:
            if self.is_boomerang:
                if self.current_frame_idx >= len(self.frames):
                    self.play_direction = -1
                    self.current_frame_idx = len(self.frames) - 2
                    if self.current_frame_idx < 0:
                        self.current_frame_idx = 0
                else:
                    self.play_direction = 1
                    self.current_frame_idx = 1
                    if self.current_frame_idx >= len(self.frames):
                        self.current_frame_idx = len(self.frames) - 1
            elif self.is_looping:
                self.current_frame_idx = 0
            else:
                self.current_frame_idx = len(self.frames) - 1
                self.stop_anim()
                return
                
        self.update_player_selection()
        
    def update_player_selection(self):
        if 0 <= self.current_frame_idx < self.list_widget.count():
            item = self.list_widget.item(self.current_frame_idx)
            # Temporarily block signals to avoid triggering a reload loop if we don't want it,
            # but we DO want the painter to update! So let it emit.
            self.list_widget.setCurrentItem(item)
            # Ensure it's visible in the scroll area
            self.list_widget.scrollToItem(item)
            self.update_player_label()
            
    def update_player_label(self):
        total = len(self.frames)
        idx = self.current_frame_idx + 1 if total > 0 else 0
        self.player_label.setText(f"Frame: {idx}/{total}")
