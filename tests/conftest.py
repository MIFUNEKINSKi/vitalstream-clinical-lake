"""Shared pytest fixtures for VitalStream tests."""

import json
import os

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Session-scoped local SparkSession for testing."""
    session = (
        SparkSession.builder
        .master("local[1]")
        .appName("vitalstream-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def sample_bundle_path():
    """Path to the sample FHIR bundle fixture."""
    return os.path.join(
        os.path.dirname(__file__), "fixtures", "sample_fhir_bundle.json"
    )


@pytest.fixture
def sample_bundle_dict():
    """Load sample FHIR bundle as a Python dict."""
    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "sample_fhir_bundle.json"
    )
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def invalid_bundle_dict():
    """Load invalid FHIR bundle as a Python dict."""
    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "invalid_fhir_bundle.json"
    )
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def sample_bundle_df(spark, sample_bundle_path):
    """Load sample FHIR bundle as a Spark DataFrame."""
    return spark.read.option("multiline", "true").json(sample_bundle_path)
