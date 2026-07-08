import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def loaders():
    train_tf = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(0.2, 0.2, 0.2),
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    train = datasets.ImageFolder(os.path.join(ROOT, "dataset", "train"), train_tf)
    val = datasets.ImageFolder(os.path.join(ROOT, "dataset", "val"), val_tf)
    return (DataLoader(train, batch_size=16, shuffle=True),
            DataLoader(val, batch_size=16), train.classes)


def run(loader, model, crit, opt, train):
    model.train() if train else model.eval()
    total, correct, loss_sum = 0, 0, 0.0
    for x, y in loader:
        if train:
            opt.zero_grad()
        out = model(x)
        loss = crit(out, y)
        if train:
            loss.backward()
            opt.step()
        loss_sum += loss.item() * x.size(0)
        correct += (out.argmax(1) == y).sum().item()
        total += y.size(0)
    return loss_sum / total, correct / total


def main():
    epochs = 12
    tl, vl, classes = loaders()
    print("Classes:", classes)
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    for p in model.parameters():
        p.requires_grad = False
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    crit = nn.CrossEntropyLoss()
    opt = torch.optim.Adam(model.classifier.parameters(), lr=1e-3)
    best, history = 0.0, []
    for e in range(1, epochs + 1):
        _, ta = run(tl, model, crit, opt, True)
        with torch.no_grad():
            _, va = run(vl, model, crit, opt, False)
        history.append({"epoch": e, "train_acc": round(ta, 3), "val_acc": round(va, 3)})
        print("epoch %d  train %.1f%%  val %.1f%%" % (e, ta * 100, va * 100))
        if va >= best:
            best = va
            torch.save(model.state_dict(), os.path.join(ROOT, "model.pth"))
    json.dump({"classes": classes, "best_val_acc": round(best, 3), "history": history},
              open(os.path.join(ROOT, "training", "metrics.json"), "w"), indent=2)
    print("Done. Best val %.1f%% -> model.pth" % (best * 100))


if __name__ == "__main__":
    main()
