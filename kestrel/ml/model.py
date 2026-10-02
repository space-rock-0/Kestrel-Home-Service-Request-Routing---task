from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def make_pipeline(C: float = 10.0, class_weight=None) -> Pipeline:
    pre = ColumnTransformer([
        ("w", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), "text"),
        ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, max_features=60000), "text"),
        ("m", CountVectorizer(token_pattern=r"\S+", lowercase=False, binary=True), "meta"),
    ])
    return Pipeline([("pre", pre), ("clf", LogisticRegression(C=C, class_weight=class_weight, max_iter=3000))])
