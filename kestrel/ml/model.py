from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def make_pipeline(C: float = 10.0, class_weight=None) -> Pipeline:
    """The pipeline, with one rule that is not about accuracy.

    TOKEN_PATTERN excludes any token containing a digit. A TF-IDF pipeline persists its
    vocabulary_, and the sklearn default r"(?u)\\b\\w\\w+\\b" admits digits -- so customer order
    numbers (KO2xxxxxx) and warranty serials (SR#####) were being learned into the model and
    shipped in artifacts/model.joblib. 119 of them were recoverable by unpickling the committed
    file, which made a `.gitignore` claim that the model contained "no identifiers" false.

    Those tokens are also useless: they are high-cardinality, repeat only for repeat customers,
    and can only memorise. Excluding them measured -0.0010 macro-F1 on validation, against a
    standard error of roughly 1.1 points. It is a compliance fix that costs nothing measurable.

    The char_wb vectoriser is left alone. Char n-grams still see digits, but they are fragments
    ("26","60","015") rather than whole identifiers, and none reconstruct a customer number.
    """
    pre = ColumnTransformer([
        ("w", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                              token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b"), "text"),
        ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, max_features=60000), "text"),
        ("m", CountVectorizer(token_pattern=r"\S+", lowercase=False, binary=True), "meta"),
    ])
    return Pipeline([("pre", pre), ("clf", LogisticRegression(C=C, class_weight=class_weight, max_iter=3000))])
