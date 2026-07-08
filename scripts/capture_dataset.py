import sys, os, time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
from app.inference import load_labels


def main():
    _, profile = load_labels()
    classes = profile["classes"]
    print("Show an object, then press its number key to save it:")
    for i, c in enumerate(classes):
        print("  [%d] %s" % (i + 1, c))
    print("  [q] quit")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    counts = {c: 0 for c in classes}
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        info = "   ".join("%d=%s(%d)" % (i + 1, c, counts[c]) for i, c in enumerate(classes))
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (18, 18, 18), -1)
        cv2.putText(frame, info, (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 120), 1, cv2.LINE_AA)
        cv2.imshow("Capture dataset", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        for i, c in enumerate(classes):
            if k == ord(str(i + 1)):
                split = "val" if counts[c] % 5 == 0 else "train"
                folder = os.path.join("dataset", split, c)
                os.makedirs(folder, exist_ok=True)
                cv2.imwrite(os.path.join(folder, "%d.jpg" % int(time.time() * 1000)), frame)
                counts[c] += 1
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()