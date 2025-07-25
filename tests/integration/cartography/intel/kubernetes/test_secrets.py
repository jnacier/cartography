import pytest

from cartography.intel.kubernetes.clusters import load_kubernetes_cluster
from cartography.intel.kubernetes.namespaces import load_namespaces
from cartography.intel.kubernetes.secrets import cleanup
from cartography.intel.kubernetes.secrets import load_secrets
from tests.data.kubernetes.clusters import KUBERNETES_CLUSTER_DATA
from tests.data.kubernetes.clusters import KUBERNETES_CLUSTER_IDS
from tests.data.kubernetes.clusters import KUBERNETES_CLUSTER_NAMES
from tests.data.kubernetes.namespaces import KUBERNETES_CLUSTER_1_NAMESPACES_DATA
from tests.data.kubernetes.namespaces import KUBERNETES_CLUSTER_2_NAMESPACES_DATA
from tests.data.kubernetes.secrets import KUBERNETES_SECRETS_DATA
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 123456789


@pytest.fixture
def _create_test_cluster(neo4j_session):
    load_kubernetes_cluster(
        neo4j_session,
        KUBERNETES_CLUSTER_DATA,
        TEST_UPDATE_TAG,
    )
    load_namespaces(
        neo4j_session,
        KUBERNETES_CLUSTER_1_NAMESPACES_DATA,
        TEST_UPDATE_TAG,
        KUBERNETES_CLUSTER_NAMES[0],
        KUBERNETES_CLUSTER_IDS[0],
    )
    load_namespaces(
        neo4j_session,
        KUBERNETES_CLUSTER_2_NAMESPACES_DATA,
        TEST_UPDATE_TAG,
        KUBERNETES_CLUSTER_NAMES[1],
        KUBERNETES_CLUSTER_IDS[1],
    )

    yield


def test_load_secrets(neo4j_session, _create_test_cluster):
    # Act
    load_secrets(
        neo4j_session,
        KUBERNETES_SECRETS_DATA,
        update_tag=TEST_UPDATE_TAG,
        cluster_id=KUBERNETES_CLUSTER_IDS[0],
        cluster_name=KUBERNETES_CLUSTER_NAMES[0],
    )

    # Assert: Expect that the secrets were loaded
    expected_nodes = {
        ("my-secret-1",),
        ("my-secret-2",),
    }
    assert check_nodes(neo4j_session, "KubernetesSecret", ["name"]) == expected_nodes


def test_load_secrets_relationships(neo4j_session, _create_test_cluster):
    # Act
    load_secrets(
        neo4j_session,
        KUBERNETES_SECRETS_DATA,
        update_tag=TEST_UPDATE_TAG,
        cluster_id=KUBERNETES_CLUSTER_IDS[0],
        cluster_name=KUBERNETES_CLUSTER_NAMES[0],
    )

    # Assert: Expect secrets to be in the correct namespace
    expected_rels = {
        (KUBERNETES_CLUSTER_1_NAMESPACES_DATA[-1]["name"], "my-secret-1"),
        (KUBERNETES_CLUSTER_1_NAMESPACES_DATA[-1]["name"], "my-secret-2"),
    }
    assert (
        check_rels(
            neo4j_session,
            "KubernetesNamespace",
            "name",
            "KubernetesSecret",
            "name",
            "CONTAINS",
        )
        == expected_rels
    )

    # Assert: Expect secrets to be in the correct cluster and namespace
    expected_rels = {
        (KUBERNETES_CLUSTER_NAMES[0], "my-secret-1"),
        (KUBERNETES_CLUSTER_NAMES[0], "my-secret-2"),
    }
    assert (
        check_rels(
            neo4j_session,
            "KubernetesNamespace",
            "cluster_name",
            "KubernetesSecret",
            "name",
            "CONTAINS",
        )
        == expected_rels
    )


def test_secret_cleanup(neo4j_session, _create_test_cluster):
    # Arrange
    load_secrets(
        neo4j_session,
        KUBERNETES_SECRETS_DATA,
        update_tag=TEST_UPDATE_TAG,
        cluster_id=KUBERNETES_CLUSTER_IDS[0],
        cluster_name=KUBERNETES_CLUSTER_NAMES[0],
    )

    # Act
    common_job_parameters = {
        "UPDATE_TAG": TEST_UPDATE_TAG + 1,
        "CLUSTER_ID": KUBERNETES_CLUSTER_IDS[0],
    }
    cleanup(
        neo4j_session,
        common_job_parameters,
    )

    # Assert: Expect that the secrets were deleted
    assert check_nodes(neo4j_session, "KubernetesSecret", ["name"]) == set()
