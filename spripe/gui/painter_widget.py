"""
Module docstring.
"""
import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QColorDialog,
    QGraphicsView,
    QGraphicsScene,
    QMessageBox,
    QApplication,
    QCheckBox,
    QGraphicsEllipseItem,
)
from PyQt6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QImage,
    QCursor,
    QIcon,
    QPainterPath,
    QPolygonF,
    QRegion,
    QBitmap,
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRectF, QThread


class GrabCutThread(QThread):
    """GrabCutThread class."""
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, arr, rect_cv):
        """__init__ method."""
        super().__init__()
        self.arr = arr
        self.rect_cv = rect_cv

    def run(self):
        """run method."""
        mask = np.zeros(self.arr.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(
                self.arr,
                mask,
                self.rect_cv,
                bgdModel,
                fgdModel,
                5,
                cv2.GC_INIT_WITH_RECT,
            )
            result_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype("uint8")
            self.finished_signal.emit(result_mask)
        except Exception as e:
            self.error_signal.emit(str(e))
            self.finished_signal.emit(None)


class CanvasView(QGraphicsView):
    """CanvasView class."""
    color_picked = pyqtSignal(QColor)
    selection_changed = pyqtSignal(bool)
    grabcut_error = pyqtSignal(str)
    interaction_started = pyqtSignal()

    def resizeEvent(self, event):
        """resizeEvent method."""
        super().resizeEvent(event)

    def __init__(self, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.selection_overlay = None

        self.image_path = None
        self.original_pixmap = None
        self.manual_zoom = False

        self.pinned_overlay = None

        self.current_tool = "brush"
        self.pen_color = QColor(255, 0, 0)
        self.pen_size = 10
        self.magic_wand_tolerance = 30
        self.is_soft_brush = False

        self.last_point = None
        self.drawing = False

        self.selection_mask = None
        self.selection_region = None

        self.poly_points = []
        self.poly_dots = []  # Store QGraphicsEllipseItems
        self.temp_path_item = None

        self.grabcut_points = []
        self.grabcut_thread = None

        self.setMouseTracking(True)
        self.update_cursor()
        self.setStyleSheet("background-color: transparent; border: none;")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def load_image(self, path):
        """load_image method."""
        # Preserve pinned keyframe state
        pinned_path = getattr(self, "_current_pinned_path", None)
        pinned_opacity = self.pinned_overlay.opacity() if self.pinned_overlay else 0.4

        self.clear_selection()

        self.scene.clear()
        self.pixmap_item = None
        self.selection_overlay = None
        self.image_path = None
        self.original_pixmap = None
        self.pinned_overlay = None

        if not path or not os.path.exists(path):
            return

        self.image_path = path
        self.original_pixmap = QPixmap(path)
        self.pixmap_item = self.scene.addPixmap(self.original_pixmap)

        self.selection_overlay = self.scene.addPixmap(
            QPixmap(self.original_pixmap.size())
        )
        self.selection_overlay.setZValue(10)
        self.selection_overlay.hide()

        self.scene.setSceneRect(QRectF(self.original_pixmap.rect()))
        self.resetTransform()
        self.manual_zoom = False
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.update_cursor()

        # Restore pinned keyframe if it existed
        if pinned_path:
            self.load_pinned_keyframe(pinned_path, pinned_opacity)

    def resizeEvent(self, event):
        """resizeEvent method."""
        super().resizeEvent(event)
        if (
            not self.manual_zoom
            and hasattr(self, "scene")
            and self.scene
            and self.scene.sceneRect().isValid()
        ):
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """wheelEvent method."""
        self.manual_zoom = True
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        old_pos = self.mapToScene(event.position().toPoint())

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        self.update_cursor()

    def _add_poly_dot(self, pos):
        """_add_poly_dot method."""
        dot = self.scene.addEllipse(
            pos.x() - 3,
            pos.y() - 3,
            6,
            6,
            QPen(Qt.GlobalColor.white, 1),
            QColor(0, 0, 255, 150),
        )
        dot.setZValue(25)
        self.poly_dots.append(dot)

    def mousePressEvent(self, event):
        """mousePressEvent method."""
        if not self.pixmap_item:
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            fake_event = event.clone()
            fake_event.setButton(Qt.MouseButton.LeftButton)
            fake_event.setButtons(Qt.MouseButton.LeftButton)
            super().mousePressEvent(fake_event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.interaction_started.emit()
            scene_pos = self.mapToScene(event.pos())
            x, y = int(scene_pos.x()), int(scene_pos.y())

            if self.current_tool in ["brush", "eraser"]:
                self.drawing = True
                self.last_point = scene_pos
                self.draw_on_canvas(scene_pos)

            elif self.current_tool == "eyedropper":
                image = self.pixmap_item.pixmap().toImage()
                if 0 <= x < image.width() and 0 <= y < image.height():
                    color = image.pixelColor(x, y)
                    self.color_picked.emit(color)

            elif self.current_tool == "lasso":
                self.drawing = True
                self.poly_points = [scene_pos]
                if self.temp_path_item:
                    self.scene.removeItem(self.temp_path_item)

                path = QPainterPath()
                path.moveTo(scene_pos)
                self.temp_path_item = self.scene.addPath(
                    path, QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
                )
                self.temp_path_item.setZValue(20)

            elif self.current_tool == "poly_lasso":
                if not self.drawing:
                    self.drawing = True
                    self.poly_points = [scene_pos]
                    if self.temp_path_item:
                        self.scene.removeItem(self.temp_path_item)
                    for dot in self.poly_dots:
                        self.scene.removeItem(dot)
                    self.poly_dots.clear()

                    path = QPainterPath()
                    path.moveTo(scene_pos)
                    self.temp_path_item = self.scene.addPath(
                        path, QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
                    )
                    self.temp_path_item.setZValue(20)
                    self._add_poly_dot(scene_pos)
                else:
                    self.poly_points.append(scene_pos)
                    self._add_poly_dot(scene_pos)

                    path = QPainterPath(self.poly_points[0])
                    for p in self.poly_points[1:]:
                        path.lineTo(p)
                    self.temp_path_item.setPath(path)

            elif self.current_tool == "magic_wand":
                self.apply_magic_wand(x, y)

            elif self.current_tool == "grabcut":
                self.drawing = True
                self.grabcut_points = [scene_pos, scene_pos]
                if self.temp_path_item:
                    self.scene.removeItem(self.temp_path_item)
                rect = QRectF(scene_pos, scene_pos)
                self.temp_path_item = self.scene.addRect(
                    rect, QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
                )
                self.temp_path_item.setZValue(20)

    def mouseMoveEvent(self, event):
        """mouseMoveEvent method."""
        super().mouseMoveEvent(event)
        if not self.pixmap_item:
            return

        scene_pos = self.mapToScene(event.pos())

        if self.current_tool == "eyedropper":
            image = self.pixmap_item.pixmap().toImage()
            x, y = int(scene_pos.x()), int(scene_pos.y())
            if 0 <= x < image.width() and 0 <= y < image.height():
                color = image.pixelColor(x, y)
                self.update_cursor(eyedropper_color=color)

        if self.drawing and event.buttons() & Qt.MouseButton.LeftButton:
            if self.current_tool in ["brush", "eraser"]:
                self.draw_on_canvas(scene_pos)
            elif self.current_tool == "lasso":
                self.poly_points.append(scene_pos)
                if self.temp_path_item and len(self.poly_points) > 0:
                    path = QPainterPath()
                    path.moveTo(self.poly_points[0])
                    for p in self.poly_points[1:]:
                        path.lineTo(p)
                    self.temp_path_item.setPath(path)
            elif self.current_tool == "grabcut":
                self.grabcut_points[1] = scene_pos
                if self.temp_path_item:
                    rect = QRectF(
                        self.grabcut_points[0], self.grabcut_points[1]
                    ).normalized()
                    self.temp_path_item.setRect(rect)

        elif self.drawing and self.current_tool == "poly_lasso":
            if self.temp_path_item and len(self.poly_points) > 0:
                path = QPainterPath()
                path.moveTo(self.poly_points[0])
                for p in self.poly_points[1:]:
                    path.lineTo(p)
                path.lineTo(scene_pos)
                self.temp_path_item.setPath(path)

    def mouseReleaseEvent(self, event):
        """mouseReleaseEvent method."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.update_cursor()
            return

        if not self.pixmap_item:
            return

        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            scene_pos = self.mapToScene(event.pos())

            if self.current_tool in ["brush", "eraser"]:
                self.draw_on_canvas(scene_pos)
                self.drawing = False

            elif self.current_tool == "lasso":
                self.poly_points.append(scene_pos)
                self.drawing = False
                self.apply_polygon_selection()

            elif self.current_tool == "grabcut":
                self.drawing = False
                self.apply_grabcut()

    def mouseDoubleClickEvent(self, event):
        """mouseDoubleClickEvent method."""
        if self.current_tool == "poly_lasso" and self.drawing:
            self.drawing = False
            self.apply_polygon_selection()

    def draw_on_canvas(self, current_point):
        """draw_on_canvas method."""
        if not self.pixmap_item:
            return

        pixmap = self.pixmap_item.pixmap()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.is_soft_brush)

        if self.selection_region and not self.selection_region.isEmpty():
            painter.setClipRegion(self.selection_region)

        # Standard Brush
        if not self.is_soft_brush:
            if self.current_tool == "brush":
                pen = QPen(
                    self.pen_color,
                    self.pen_size,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
                painter.setPen(pen)
                painter.setCompositionMode(
                    QPainter.CompositionMode.CompositionMode_SourceOver
                )
            elif self.current_tool == "eraser":
                pen = QPen(
                    Qt.GlobalColor.transparent,
                    self.pen_size,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
                painter.setPen(pen)
                painter.setCompositionMode(
                    QPainter.CompositionMode.CompositionMode_Clear
                )

            if self.last_point == current_point:
                painter.setBrush(painter.pen().color())
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(current_point, self.pen_size / 2, self.pen_size / 2)
            else:
                painter.drawLine(self.last_point, current_point)

        # Soft Brush (Layered Stroke)
        else:
            base_color = (
                self.pen_color if self.current_tool == "brush" else QColor(0, 0, 0, 255)
            )
            comp_mode = (
                QPainter.CompositionMode.CompositionMode_SourceOver
                if self.current_tool == "brush"
                else QPainter.CompositionMode.CompositionMode_DestinationOut
            )
            painter.setCompositionMode(comp_mode)

            steps = 8
            for i in range(steps, 0, -1):
                size = self.pen_size * (i / steps)
                alpha = int(255 * (1.0 / steps))
                color = QColor(
                    base_color.red(), base_color.green(), base_color.blue(), alpha
                )
                pen = QPen(
                    color,
                    size,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
                painter.setPen(pen)

                if self.last_point == current_point:
                    painter.setBrush(color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(current_point, size / 2, size / 2)
                else:
                    painter.drawLine(self.last_point, current_point)

        painter.end()
        self.last_point = current_point
        self.pixmap_item.setPixmap(pixmap)

    # --- Selection Methods ---
    def apply_polygon_selection(self):
        """apply_polygon_selection method."""
        if self.temp_path_item:
            self.scene.removeItem(self.temp_path_item)
            self.temp_path_item = None

        for dot in self.poly_dots:
            self.scene.removeItem(dot)
        self.poly_dots.clear()

        if len(self.poly_points) < 3:
            return

        w, h = self.original_pixmap.width(), self.original_pixmap.height()
        arr = np.zeros((h, w), dtype=np.uint8)
        pts = np.array([[int(p.x()), int(p.y())] for p in self.poly_points], np.int32)
        cv2.fillPoly(arr, [pts], 255)

        self.set_selection_from_numpy(arr)

    def apply_magic_wand(self, x, y):
        """apply_magic_wand method."""
        img = (
            self.pixmap_item.pixmap()
            .toImage()
            .convertToFormat(QImage.Format.Format_ARGB32)
        )
        ptr = img.bits()
        ptr.setsize(img.sizeInBytes())
        arr = np.array(ptr).reshape((img.height(), img.width(), 4))

        bgr = arr[:, :, :3].copy()

        mask = np.zeros((img.height() + 2, img.width() + 2), np.uint8)
        diff = (
            self.magic_wand_tolerance,
            self.magic_wand_tolerance,
            self.magic_wand_tolerance,
        )

        flags = 8 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
        cv2.floodFill(bgr, mask, (x, y), (255, 255, 255), diff, diff, flags)

        result_mask = mask[1:-1, 1:-1]
        self.set_selection_from_numpy(result_mask)

    def apply_grabcut(self):
        """apply_grabcut method."""
        if self.temp_path_item:
            self.scene.removeItem(self.temp_path_item)
            self.temp_path_item = None

        rect = QRectF(self.grabcut_points[0], self.grabcut_points[1]).normalized()
        x = int(max(0, rect.x()))
        y = int(max(0, rect.y()))
        w = int(min(self.original_pixmap.width() - x, rect.width()))
        h = int(min(self.original_pixmap.height() - y, rect.height()))

        if w <= 1 or h <= 1:
            return

        img = (
            self.pixmap_item.pixmap()
            .toImage()
            .convertToFormat(QImage.Format.Format_RGB888)
        )
        ptr = img.bits()
        ptr.setsize(img.sizeInBytes())
        arr = np.array(ptr).reshape((img.height(), img.width(), 3))

        rect_cv = (x, y, w, h)

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.grabcut_thread = GrabCutThread(arr, rect_cv)
        self.grabcut_thread.finished_signal.connect(self.on_grabcut_finished)
        self.grabcut_thread.error_signal.connect(self.grabcut_error.emit)
        self.grabcut_thread.start()

    def on_grabcut_finished(self, result_mask):
        """on_grabcut_finished method."""
        QApplication.restoreOverrideCursor()
        if result_mask is not None:
            self.set_selection_from_numpy(result_mask)

    def keyPressEvent(self, event):
        """keyPressEvent method."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            # If drawing a polygon, delete the last point
            if (
                self.drawing
                and self.current_tool == "poly_lasso"
                and len(self.poly_points) > 0
            ):
                self.poly_points.pop()
                last_dot = self.poly_dots.pop()
                self.scene.removeItem(last_dot)

                if len(self.poly_points) > 0:
                    path = QPainterPath()
                    path.moveTo(self.poly_points[0])
                    for p in self.poly_points[1:]:
                        path.lineTo(p)
                    self.temp_path_item.setPath(path)
                else:
                    self.temp_path_item.setPath(QPainterPath())
            else:
                self.delete_selection_content()
        else:
            super().keyPressEvent(event)

    def delete_selection_content(self):
        """delete_selection_content method."""
        if (
            not self.pixmap_item
            or not self.selection_region
            or self.selection_region.isEmpty()
        ):
            return

        pixmap = self.pixmap_item.pixmap()
        painter = QPainter(pixmap)
        painter.setClipRegion(self.selection_region)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(pixmap.rect(), Qt.GlobalColor.transparent)
        painter.end()

        self.pixmap_item.setPixmap(pixmap)

    def set_selection_from_numpy(self, mask_np, is_smooth_update=False):
        """set_selection_from_numpy method."""
        self.selection_mask = mask_np
        if not is_smooth_update:
            self.original_selection_mask = mask_np.copy()

        h, w = mask_np.shape
        inverted_mask = 255 - mask_np
        self._mask_bytes = inverted_mask.tobytes()
        img = QImage(self._mask_bytes, w, h, w, QImage.Format.Format_Grayscale8)
        mono_img = img.convertToFormat(QImage.Format.Format_MonoLSB)
        bitmap = QBitmap.fromImage(mono_img)
        self.selection_region = QRegion(bitmap)

        self.update_selection_overlay()
        if not is_smooth_update:
            self.selection_changed.emit(True)

    def smooth_selection(self, blur_pixels):
        """smooth_selection method."""
        if (
            not hasattr(self, "original_selection_mask")
            or self.original_selection_mask is None
        ):
            return

        if blur_pixels <= 0:
            self.set_selection_from_numpy(self.original_selection_mask.copy(), True)
            return

        ksize = (blur_pixels * 2 + 1, blur_pixels * 2 + 1)
        blurred = cv2.GaussianBlur(self.original_selection_mask, ksize, 0)
        _, thresholded = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)

        self.set_selection_from_numpy(thresholded, True)

    def update_selection_overlay(self):
        """update_selection_overlay method."""
        if self.selection_mask is None:
            if self.selection_overlay:
                self.selection_overlay.hide()
            return

        h, w = self.selection_mask.shape
        overlay_img = QImage(w, h, QImage.Format.Format_ARGB32)
        overlay_img.fill(Qt.GlobalColor.transparent)

        self._overlay_mask_bytes = self.selection_mask.tobytes()
        mask_qimg = QImage(
            self._overlay_mask_bytes, w, h, w, QImage.Format.Format_Alpha8
        )

        painter = QPainter(overlay_img)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(overlay_img.rect(), QColor(255, 0, 0, 100))
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_DestinationIn
        )
        painter.drawImage(0, 0, mask_qimg)
        painter.end()

        self.selection_overlay.setPixmap(QPixmap.fromImage(overlay_img))
        self.selection_overlay.show()

    def clear_selection(self):
        """clear_selection method."""
        self.drawing = False
        self.selection_mask = None
        self.selection_region = None

        self.poly_points.clear()
        for dot in self.poly_dots:
            if dot.scene() == self.scene:
                self.scene.removeItem(dot)
        self.poly_dots.clear()

        if self.selection_overlay:
            self.selection_overlay.hide()
        if self.temp_path_item:
            if self.temp_path_item.scene() == self.scene:
                self.scene.removeItem(self.temp_path_item)
            self.temp_path_item = None

    def load_pinned_keyframe(self, path, opacity=0.4):
        """load_pinned_keyframe method."""
        self.clear_pinned_keyframe()
        self._current_pinned_path = path
        if not path or not os.path.exists(path):
            return

        pixmap = QPixmap(path)
        self.pinned_overlay = self.scene.addPixmap(pixmap)
        self.pinned_overlay.setZValue(5)
        self.pinned_overlay.setOpacity(opacity)
        self.pinned_overlay.show()

    def set_pinned_opacity(self, opacity):
        """set_pinned_opacity method."""
        if self.pinned_overlay:
            self.pinned_overlay.setOpacity(opacity)

    def clear_pinned_keyframe(self):
        """clear_pinned_keyframe method."""
        self._current_pinned_path = None
        if self.pinned_overlay:
            # Check if it is still in the scene to avoid C++ deletion errors
            if self.pinned_overlay.scene() == self.scene:
                self.scene.removeItem(self.pinned_overlay)
            self.pinned_overlay = None

    def reload_image(self):
        """reload_image method."""
        if self.image_path:
            self.load_image(self.image_path)

    def save_image(self):
        """save_image method."""
        if self.image_path and self.pixmap_item:
            pixmap = self.pixmap_item.pixmap()
            pixmap.save(self.image_path, "PNG")

    def update_cursor(self, eyedropper_color=None):
        """update_cursor method."""
        if self.current_tool in ["brush", "eraser"]:
            size = self.pen_size
            if size < 2:
                size = 2

            transform_scale = (
                self.transform().m11() if self.transform().m11() > 0 else 1.0
            )
            visual_size = max(2, int(self.pen_size * self.transform().m11()))

            # Windows limits custom cursor size (often to 128x128 max) and will glitch out if exceeded.
            # If the user zooms in super far, just fallback to a precision crosshair.
            if visual_size > 128:
                self.setCursor(Qt.CursorShape.CrossCursor)
                return

            cursor_pix = QPixmap(visual_size + 4, visual_size + 4)
            cursor_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(cursor_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            if self.current_tool == "brush":
                color = self.pen_color
                if self.is_soft_brush:
                    color.setAlpha(100)
                painter.setBrush(color)
            else:
                painter.setBrush(Qt.GlobalColor.transparent)

            painter.drawEllipse(2, 2, visual_size, visual_size)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawEllipse(2, 2, visual_size, visual_size)
            painter.end()

            self.setCursor(QCursor(cursor_pix))

        elif self.current_tool == "eyedropper" and eyedropper_color:
            cursor_pix = QPixmap(24, 24)
            cursor_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(cursor_pix)
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.setBrush(eyedropper_color)
            painter.drawRect(8, 8, 12, 12)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(0, 0, 8, 8)
            painter.end()
            self.setCursor(QCursor(cursor_pix, 0, 0))

        else:
            self.setCursor(Qt.CursorShape.CrossCursor)


class PainterWidget(QWidget):
    """PainterWidget class."""
    def __init__(self, settings_manager, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.icon_dir = os.path.join(os.path.dirname(__file__), "icons")
        self.init_ui()

    def get_icon(self, name):
        """get_icon method."""
        return QIcon(os.path.join(self.icon_dir, f"{name}.svg"))

    def on_settings_changed(self, key, value):
        """on_settings_changed method."""
        if key == "onion_visible_default":
            self.chk_onion.setChecked(value)
        elif key == "onion_opacity_default":
            self.slider_onion.setValue(value)
            self.update_onion_opacity()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tools CSS to highlight active button
        self.setStyleSheet("""
            QPushButton:checked {
                background-color: #0078D7;
                border: 1px solid #55AAFF;
                border-radius: 4px;
            }
        """)

        toolbar = QHBoxLayout()

        self.btn_brush = QPushButton()
        self.btn_brush.setIcon(self.get_icon("brush"))
        self.btn_brush.setToolTip("Brush")
        self.btn_brush.setCheckable(True)
        self.btn_brush.setChecked(True)

        self.btn_eraser = QPushButton()
        self.btn_eraser.setIcon(self.get_icon("eraser"))
        self.btn_eraser.setToolTip("Eraser")
        self.btn_eraser.setCheckable(True)

        self.btn_eyedropper = QPushButton()
        self.btn_eyedropper.setIcon(self.get_icon("eyedropper"))
        self.btn_eyedropper.setToolTip("Eyedropper")
        self.btn_eyedropper.setCheckable(True)

        self.btn_lasso = QPushButton()
        self.btn_lasso.setIcon(self.get_icon("lasso"))
        self.btn_lasso.setToolTip("Freehand Lasso")
        self.btn_lasso.setCheckable(True)

        self.btn_poly_lasso = QPushButton()
        self.btn_poly_lasso.setIcon(self.get_icon("poly_lasso"))
        self.btn_poly_lasso.setToolTip("Polygonal Lasso")
        self.btn_poly_lasso.setCheckable(True)

        self.btn_magic_wand = QPushButton()
        self.btn_magic_wand.setIcon(self.get_icon("magic_wand"))
        self.btn_magic_wand.setToolTip("Magic Wand")
        self.btn_magic_wand.setCheckable(True)

        self.btn_grabcut = QPushButton()
        self.btn_grabcut.setIcon(self.get_icon("grabcut"))
        self.btn_grabcut.setToolTip("Quick Selection (GrabCut)")
        self.btn_grabcut.setCheckable(True)

        self.btn_clear_sel = QPushButton()
        self.btn_clear_sel.setIcon(self.get_icon("clear_selection"))
        self.btn_clear_sel.setToolTip("Clear Selection")
        self.btn_clear_sel.clicked.connect(self.clear_selection)

        tool_btns = [
            self.btn_brush,
            self.btn_eraser,
            self.btn_eyedropper,
            self.btn_lasso,
            self.btn_poly_lasso,
            self.btn_magic_wand,
            self.btn_grabcut,
        ]

        for name, btn in zip(
            [
                "brush",
                "eraser",
                "eyedropper",
                "lasso",
                "poly_lasso",
                "magic_wand",
                "grabcut",
            ],
            tool_btns,
        ):
            btn.clicked.connect(lambda checked, n=name: self.set_tool(n))
            toolbar.addWidget(btn)

        toolbar.addWidget(self.btn_clear_sel)

        # Soft Brush Toggle
        self.chk_soft = QCheckBox("Soft")
        self.chk_soft.stateChanged.connect(self.toggle_soft_brush)
        toolbar.addWidget(self.chk_soft)

        self.btn_color = QPushButton("")
        self.btn_color.setFixedSize(30, 30)
        self.btn_color.setToolTip("Current Color")
        self.btn_color.clicked.connect(self.pick_color)
        toolbar.addWidget(self.btn_color)

        self.lbl_size = QLabel("Size:")
        toolbar.addWidget(self.lbl_size)
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(1, 150)
        self.slider_size.setValue(10)
        self.slider_size.setFixedWidth(100)
        self.slider_size.valueChanged.connect(self.change_size)
        toolbar.addWidget(self.slider_size)

        toolbar.addStretch()

        # Selection Smoothing Toolkit (Hidden by default)
        self.smooth_toolbar = QWidget()
        smooth_layout = QHBoxLayout(self.smooth_toolbar)
        smooth_layout.setContentsMargins(0, 0, 0, 0)
        smooth_layout.addWidget(QLabel("Smooth Edge:"))
        self.slider_smooth = QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth.setRange(0, 15)
        self.slider_smooth.setValue(0)
        self.slider_smooth.setFixedWidth(80)
        self.slider_smooth.valueChanged.connect(self.apply_smoothing)
        smooth_layout.addWidget(self.slider_smooth)
        self.smooth_toolbar.hide()
        toolbar.addWidget(self.smooth_toolbar)

        # Onion Skin (Pinned Keyframe) Opacity Toolkit
        self.onion_toolbar = QWidget()
        onion_layout = QHBoxLayout(self.onion_toolbar)
        onion_layout.setContentsMargins(0, 0, 0, 0)

        self.chk_onion = QCheckBox("📌 Onion:")
        default_onion_visible = self.settings_manager.get("onion_visible_default", True)
        self.chk_onion.setChecked(default_onion_visible)
        self.chk_onion.toggled.connect(self.update_onion_opacity)
        onion_layout.addWidget(self.chk_onion)

        self.slider_onion = QSlider(Qt.Orientation.Horizontal)
        self.slider_onion.setRange(0, 100)
        self.slider_onion.setValue(
            self.settings_manager.get("onion_opacity_default", 40)
        )
        self.slider_onion.setFixedWidth(80)
        self.slider_onion.valueChanged.connect(self.update_onion_opacity)
        onion_layout.addWidget(self.slider_onion)

        self.onion_toolbar.hide()
        toolbar.addWidget(self.onion_toolbar)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setIcon(self.get_icon("cancel"))
        self.btn_cancel.clicked.connect(self.cancel_edits)
        self.btn_cancel.setEnabled(False)
        toolbar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save")
        self.btn_save.setIcon(self.get_icon("save"))
        self.btn_save.setObjectName("primaryAction")
        self.btn_save.clicked.connect(self.save_frame)
        self.btn_save.setEnabled(False)
        toolbar.addWidget(self.btn_save)

        # Save shortcut (Ctrl+S)
        from PyQt6.QtGui import QShortcut, QKeySequence

        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_frame)

        layout.addLayout(toolbar)

        canvas_container = QWidget()
        canvas_container.setStyleSheet("background-color: #121212; border-radius: 8px;")
        container_layout = QVBoxLayout(canvas_container)
        container_layout.setContentsMargins(10, 10, 10, 10)

        self.canvas = CanvasView()
        self.canvas.color_picked.connect(self.set_color_from_eyedropper)
        self.canvas.selection_changed.connect(self.on_selection_changed)
        self.canvas.grabcut_error.connect(
            lambda e: QMessageBox.critical(
                self, "GrabCut Error", f"GrabCut failed:\n{e}"
            )
        )
        self.interaction_started = self.canvas.interaction_started
        container_layout.addWidget(self.canvas)

        layout.addWidget(canvas_container, 1)

        self.update_color_btn(QColor(255, 0, 0))

        from spripe.core.signal_manager import SignalManager

        SignalManager.get_instance().settings_changed.connect(self.on_settings_changed)

    def on_selection_changed(self, active):
        """on_selection_changed method."""
        if active:
            self.smooth_toolbar.show()
        else:
            self.smooth_toolbar.hide()

    def set_tool(self, tool_name):
        """set_tool method."""
        self.canvas.current_tool = tool_name
        self.btn_brush.setChecked(tool_name == "brush")
        self.btn_eraser.setChecked(tool_name == "eraser")
        self.btn_eyedropper.setChecked(tool_name == "eyedropper")
        self.btn_lasso.setChecked(tool_name == "lasso")
        self.btn_poly_lasso.setChecked(tool_name == "poly_lasso")
        self.btn_magic_wand.setChecked(tool_name == "magic_wand")
        self.btn_grabcut.setChecked(tool_name == "grabcut")

        # Toggle label and slider visibility based on tool
        if tool_name == "magic_wand":
            self.lbl_size.setText("Tolerance:")
            self.lbl_size.show()
            self.slider_size.show()
        elif tool_name in ["brush", "eraser"]:
            self.lbl_size.setText("Size:")
            self.lbl_size.show()
            self.slider_size.show()
        else:
            self.lbl_size.hide()
            self.slider_size.hide()

        # Toggle soft brush checkbox visibility
        if tool_name in ["brush", "eraser"]:
            self.chk_soft.show()
        else:
            self.chk_soft.hide()

        # Toggle color button visibility
        if tool_name in ["brush", "eyedropper"]:
            self.btn_color.show()
        else:
            self.btn_color.hide()

        self.canvas.update_cursor()

    def toggle_soft_brush(self, state):
        """toggle_soft_brush method."""
        self.canvas.is_soft_brush = state == Qt.CheckState.Checked.value
        self.canvas.update_cursor()

    def apply_smoothing(self, value):
        """apply_smoothing method."""
        self.canvas.smooth_selection(value)

    def clear_selection(self):
        """clear_selection method."""
        self.canvas.clear_selection()
        self.smooth_toolbar.hide()
        self.slider_smooth.blockSignals(True)
        self.slider_smooth.setValue(0)
        self.slider_smooth.blockSignals(False)

    def pick_color(self):
        """pick_color method."""
        dialog = QColorDialog(self.canvas.pen_color, self)
        dialog.setStyleSheet("")
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, False)

        if dialog.exec():
            color = dialog.currentColor()
            if color.isValid():
                self.set_color_from_eyedropper(color)

    def set_color_from_eyedropper(self, color):
        """set_color_from_eyedropper method."""
        self.canvas.pen_color = color
        self.update_color_btn(color)
        self.set_tool("brush")

    def update_color_btn(self, color):
        """update_color_btn method."""
        self.btn_color.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #FFF;"
        )
        self.canvas.update_cursor()

    def change_size(self, size):
        """change_size method."""
        self.canvas.pen_size = size
        self.canvas.magic_wand_tolerance = size
        self.canvas.update_cursor()

    def load_frame(self, frame_path):
        """load_frame method."""
        self.canvas.load_image(frame_path)
        has_frame = bool(frame_path)
        self.btn_save.setEnabled(has_frame)
        self.btn_cancel.setEnabled(has_frame)
        self.smooth_toolbar.hide()

    def save_frame(self):
        """save_frame method."""
        if not self.btn_save.isEnabled():
            return
        self.canvas.save_image()

        # Visual success feedback
        original_text = self.btn_save.text()
        original_style = self.btn_save.styleSheet()
        self.btn_save.setText("Saved!")
        self.btn_save.setStyleSheet(
            "background-color: #28a745; color: white; border: none; border-radius: 4px;"
        )

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(
            1500, lambda: self.reset_save_btn(original_text, original_style)
        )

    def reset_save_btn(self, text, style):
        """reset_save_btn method."""
        self.btn_save.setText(text)
        self.btn_save.setStyleSheet(style)

    def update_onion_opacity(self, *args):
        """update_onion_opacity method."""
        if self.chk_onion.isChecked():
            opacity = self.slider_onion.value() / 100.0
        else:
            opacity = 0.0
        self.canvas.set_pinned_opacity(opacity)

    def cancel_edits(self):
        """cancel_edits method."""
        self.canvas.reload_image()

    def on_pinned_keyframe_updated(self, path):
        """on_pinned_keyframe_updated method."""
        if path and os.path.exists(path):
            self.onion_toolbar.show()
            self.update_onion_opacity()
            # Still load the keyframe into the canvas but opacity handles visibility
            self.canvas.load_pinned_keyframe(
                path,
                (
                    self.slider_onion.value() / 100.0
                    if self.chk_onion.isChecked()
                    else 0.0
                ),
            )
        else:
            self.canvas.clear_pinned_keyframe()
            self.onion_toolbar.hide()
