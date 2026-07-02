"""Tests for cursor pagination params on the widened search methods."""

from unittest.mock import patch

from conduit.client.diffusion import DiffusionClient
from conduit.client.file import FileClient
from conduit.client.project import ProjectClient


class TestDiffusionClientSearchPagination:
    """Test cursor pagination params on DiffusionClient search methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = DiffusionClient(
            api_url="http://test.example.com/api/", api_token="test_token"
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_repositories_forwards_pagination_params(
        self, mock_request
    ):
        """Pagination params are serialized into the request payload."""
        mock_request.return_value = {"data": []}

        self.client.search_repositories(
            order="newest", before="10", after="42", limit=50
        )

        mock_request.assert_called_once_with(
            "diffusion.repository.search",
            {
                "limit": 50,
                "order": "newest",
                "before": "10",
                "after": "42",
            },
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_repositories_omits_pagination_by_default(
        self, mock_request
    ):
        """Pagination params are absent from the payload when unset."""
        mock_request.return_value = {"data": []}

        self.client.search_repositories()

        mock_request.assert_called_once_with(
            "diffusion.repository.search", {"limit": 100}
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_commits_forwards_pagination_params(self, mock_request):
        """Pagination params are serialized into the request payload."""
        mock_request.return_value = {"data": []}

        self.client.search_commits(
            order="newest", before="10", after="42", limit=50
        )

        mock_request.assert_called_once_with(
            "diffusion.commit.search",
            {
                "limit": 50,
                "order": "newest",
                "before": "10",
                "after": "42",
            },
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_commits_omits_pagination_by_default(
        self, mock_request
    ):
        """Pagination params are absent from the payload when unset."""
        mock_request.return_value = {"data": []}

        self.client.search_commits()

        mock_request.assert_called_once_with(
            "diffusion.commit.search", {"limit": 100}
        )


class TestFileClientSearchPagination:
    """Test cursor pagination params on FileClient.search_files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = FileClient(
            api_url="http://test.example.com/api/", api_token="test_token"
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_files_forwards_pagination_params(self, mock_request):
        """Pagination params are serialized into the request payload."""
        mock_request.return_value = {"data": []}

        self.client.search_files(
            order="newest", before="10", after="42", limit=50
        )

        mock_request.assert_called_once_with(
            "file.search",
            {
                "limit": 50,
                "order": "newest",
                "before": "10",
                "after": "42",
            },
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_files_omits_pagination_by_default(self, mock_request):
        """Pagination params are absent from the payload when unset."""
        mock_request.return_value = {"data": []}

        self.client.search_files()

        mock_request.assert_called_once_with(
            "file.search", {"limit": 100}
        )


class TestProjectClientSearchPagination:
    """Test cursor pagination params on ProjectClient search methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = ProjectClient(
            api_url="http://test.example.com/api/", api_token="test_token"
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_projects_forwards_pagination_params(
        self, mock_request
    ):
        """Pagination params are serialized into the request payload."""
        mock_request.return_value = {"data": []}

        self.client.search_projects(
            order="newest", before="10", after="42", limit=50
        )

        mock_request.assert_called_once_with(
            "project.search",
            {
                "limit": 50,
                "order": "newest",
                "before": "10",
                "after": "42",
            },
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_projects_omits_pagination_by_default(
        self, mock_request
    ):
        """Pagination params are absent from the payload when unset."""
        mock_request.return_value = {"data": []}

        self.client.search_projects()

        mock_request.assert_called_once_with(
            "project.search", {"limit": 100}
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_columns_forwards_pagination_params(
        self, mock_request
    ):
        """Pagination params are serialized into the request payload."""
        mock_request.return_value = {"data": []}

        self.client.search_columns(
            order="newest", before="10", after="42", limit=50
        )

        mock_request.assert_called_once_with(
            "project.column.search",
            {
                "limit": 50,
                "order": "newest",
                "before": "10",
                "after": "42",
            },
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_columns_omits_pagination_by_default(
        self, mock_request
    ):
        """Pagination params are absent from the payload when unset."""
        mock_request.return_value = {"data": []}

        self.client.search_columns()

        mock_request.assert_called_once_with(
            "project.column.search", {"limit": 100}
        )
