import sys, os, time
from collections import deque, Counter
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
from app.inference import Predictor, load_labels

THRESHOLD = 0.65        # below this = "uncertain", no committed label
WINDOW = 7              # how many recent predictions to vote over


def main():
    _, profile = load_labels()
    colors = profile.get("colors", {})
    predictor = Predictor()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Cannot open webcam. Close Zoom/Teams/WhatsApp and check camera permissions.")
        return

    recent = deque(maxlen=WINDOW)
    label, conf, last = "-", 0.0, 0.0
    print("Mode:", predictor.version, "| q = quit, s = save frame")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = time.time()
        if now - last > 0.25:                       # predict ~4x per second
            c, cf = predictor.predict(frame)
            recent.append((c, cf))
            last = now

        # majority vote over the recent window, averaged confidence
        if recent:
            votes = Counter(c for c, _ in recent)
            top, _ = votes.most_common(1)[0]
            confs = [cf for c, cf in recent if c == top]
            avg = sum(confs) / len(confs)
            if avg >= THRESHOLD:
                label, conf = top, avg
            else:
                label, conf = "Uncertain", avg

        # draw
        if label == "Uncertain":
            bgr = (60, 165, 255)                     # orange
            text = "Uncertain  %.0f%%" % (conf * 100)
        else:
            hexc = colors.get(label, "#2e9e5b").lstrip("#")
            bgr = tuple(int(hexc[i:i + 2], 16) for i in (4, 2, 0))
            text = "%s  %.0f%%" % (label, conf * 100)

        h, w = frame.shape[:2]
        s = int(min(h, w) * 0.6)
        cv2.rectangle(frame, ((w - s) // 2, (h - s) // 2), ((w + s) // 2, (h + s) // 2), bgr, 2)
        cv2.rectangle(frame, (0, 0), (w, 72), (18, 18, 18), -1)
        cv2.putText(frame, text, (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.2, bgr, 2, cv2.LINE_AA)
        cv2.imshow("Waste AI - Live", frame)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord("s"):
            os.makedirs("shots", exist_ok=True)
            cv2.imwrite("shots/%d.jpg" % int(now), frame)
            print("saved")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()