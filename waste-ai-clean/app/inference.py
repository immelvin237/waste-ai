import json, os, random
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = os.path.join(ROOT, "model.pth")
LABELS = os.path.join(ROOT, "labels.json")

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def load_labels():
    with open(LABELS, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["active"], cfg["profiles"][cfg["active"]]


class Predictor:
    def __init__(self):
        _, profile = load_labels()
        self.classes = profile["classes"]
        self.model = None
        self.torch = None
        self.version = "simulation"
        self._load()

    def _load(self):
        if not os.path.exists(WEIGHTS):
            return
        try:
            import torch
            from torchvision.models import efficientnet_b0
            model = efficientnet_b0(weights=None)
            in_f = model.classifier[1].in_features
            model.classifier[1] = torch.nn.Linear(in_f, len(self.classes))
            model.load_state_dict(torch.load(WEIGHTS, map_location="cpu"))
            model.eval()
            self.torch, self.model, self.version = torch, model, "efficientnet_b0"
        except Exception as e:
            print("model load failed, staying in simulation:", e)

    def preprocess(self, frame_bgr):
        import cv2
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (224, 224)).astype(np.float32) / 255.0
        rgb = (rgb - MEAN) / STD
        return np.transpose(rgb, (2, 0, 1))[None, :]

    def predict(self, frame_bgr):
        if self.model is None:
            return random.choice(self.classes), random.uniform(0.6, 0.99)
        x = self.torch.from_numpy(self.preprocess(frame_bgr))
        with self.torch.no_grad():
            probs = self.torch.softmax(self.model(x), dim=1)[0]
            conf, idx = probs.max(0)
        return self.classes[int(idx)], float(conf)

    def predict_bytes(self, data):
        import cv2
        arr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return self.predict(frame)
