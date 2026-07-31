"""Unit tests for FeatureEngineeringService."""

from app.services.data.feature_engineering_service import FeatureEngineeringService


def test_engineer_features_produces_at_least_30_features(sample_raw_dataframe):
    enriched_df, feature_names = FeatureEngineeringService().engineer_features(sample_raw_dataframe)

    assert len(feature_names) >= 30
    assert len(enriched_df) == len(sample_raw_dataframe)


def test_engineered_features_have_no_missing_values(sample_raw_dataframe):
    enriched_df, feature_names = FeatureEngineeringService().engineer_features(sample_raw_dataframe)

    assert not enriched_df[feature_names].isna().any().any()


def test_risk_scores_are_bounded(sample_raw_dataframe):
    enriched_df, _ = FeatureEngineeringService().engineer_features(sample_raw_dataframe)

    for col in ("TemperatureRiskScore", "PressureRiskScore", "VibrationRiskScore"):
        assert enriched_df[col].between(0, 2).all()

    assert enriched_df["EquipmentAgeScore"].between(0, 1).all()
    assert enriched_df["MaintenancePriority"].between(0, 3).all()
    assert enriched_df["EquipmentConditionScore"].between(0, 3).all()


def test_equipment_type_is_one_hot_encoded(sample_raw_dataframe):
    enriched_df, feature_names = FeatureEngineeringService().engineer_features(sample_raw_dataframe)

    assert "EquipmentType_Excavator" in feature_names
    assert "EquipmentType_Loader" in feature_names
    assert set(enriched_df["EquipmentType_Excavator"].unique()) <= {0, 1}
