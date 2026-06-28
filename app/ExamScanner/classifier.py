import os, re, json, pickle
import numpy as np

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
DATA_PATH  = os.path.join(BASE_DIR, "training_data.json")

def features(tok):
    w = str(tok.get("text", tok.get("word","")))
    n = str(tok.get("next_word",""))
    return [float(bool(re.fullmatch(r"\d+",w))),
            float(6 <= len(w) <= 12),
            float(bool(re.match(r"[,A-Za-z]",n)))]

class FieldClassifier:
    def __init__(self):
        self.model = self.le = None; self.trained = False

    def train(self, path=DATA_PATH, verbose=True):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.metrics import accuracy_score
        data = json.load(open(path))
        X = np.array([features(s) for s in data], dtype=np.float32)
        y = np.array([s["label"] for s in data])
        self.le = LabelEncoder(); self.le.fit(sorted(set(y)))
        ye = self.le.transform(y)
        n  = len(X)
        Xt,Xe,yt,ye_ = train_test_split(X,ye,test_size=max(0.2,2/n),
                        random_state=42, stratify=ye if n>=4 else None)
        self.model = RandomForestClassifier(100, max_depth=6,
                     class_weight="balanced", random_state=42)
        self.model.fit(Xt,yt); self.trained = True
        from sklearn.model_selection import cross_val_score
        cv_m = float(cross_val_score(self.model, X, ye, cv=min(5,n//4),
                     scoring="accuracy").mean()) if n >= 20 else 0.0
        from sklearn.metrics import accuracy_score
        if verbose: print(f"  Accuracy={acc:.1%}")
        return {"accuracy": round(acc,4)}

    def predict(self, tok):
        if not self.trained: raise RuntimeError("Not trained")
        p = self.model.predict_proba(
            np.array(features(tok), dtype=np.float32).reshape(1,-1))[0]
        i = int(np.argmax(p))
        return self.le.inverse_transform([i])[0], float(p[i])

    def save(self, path=MODEL_PATH):
        pickle.dump({"model":self.model,"le":self.le,"trained":self.trained},
                    open(path,"wb"))
        print(f"  Saved → {path}")

    @classmethod
    def load(cls, path=MODEL_PATH):
        if not os.path.exists(path):
            print("[ML] model.pkl missing — run train.py"); return None
        d = pickle.load(open(path,"rb"))
        c = cls(); c.model=d["model"]; c.le=d["le"]; c.trained=d["trained"]
        return c