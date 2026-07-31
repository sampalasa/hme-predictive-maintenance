"""Feature selection comparison page (MI, RFE, Permutation, SHAP, Variance, Boruta)."""

from flask import Blueprint, render_template
from flask_login import login_required

from app.services.ml.feature_selection_service import FeatureSelectionService

feature_selection_bp = Blueprint("feature_selection", __name__, url_prefix="/feature-selection")


@feature_selection_bp.get("")
@login_required
def index():
    service = FeatureSelectionService(sample_size=1500)
    comparison = service.compare_all_methods(top_n=15)
    return render_template("feature_selection/index.html", comparison=comparison)
