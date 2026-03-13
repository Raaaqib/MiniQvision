"""Export YOLO model from .pt to .onnx format"""
from ultralytics import YOLO
import traceback

try:
    print("Loading yolo11n.pt...")
    model = YOLO("yolo11n.pt")
    print("Exporting to ONNX...")
    path = model.export(format="onnx", imgsz=640, simplify=True)
    print(f"SUCCESS: Exported to {path}")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
