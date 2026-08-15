import app.main as main
from app.models import MAX_ETAG_CHARS, MAX_RESOURCE_HREF_CHARS
from app.vcf_models import VcfImportRequest


def _query_parameter(path: str, method: str, name: str) -> dict:
    operation = main.app.openapi()["paths"][path][method]
    parameters = {
        parameter["name"]: parameter
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "query"
    }
    return parameters[name]


def test_carddav_routes_bound_resource_hrefs() -> None:
    routes = [
        ("/api/carddav/contacts", "get", "address_book_href"),
        ("/api/carddav/contact", "get", "href"),
        ("/api/carddav/contacts", "post", "address_book_href"),
        ("/api/carddav/contact", "put", "href"),
        ("/api/carddav/contact", "delete", "href"),
        ("/api/carddav/contact/export", "get", "href"),
        ("/api/carddav/address-book/export", "get", "address_book_href"),
        ("/api/carddav/duplicates", "get", "address_book_href"),
    ]

    for path, method, name in routes:
        parameter = _query_parameter(path, method, name)
        assert parameter["schema"]["minLength"] == 1
        assert parameter["schema"]["maxLength"] == MAX_RESOURCE_HREF_CHARS


def test_primary_carddav_mutations_bound_etags() -> None:
    for method in ("put", "delete"):
        parameter = _query_parameter("/api/carddav/contact", method, "etag")
        assert parameter["schema"]["minLength"] == 1
        assert parameter["schema"]["maxLength"] == MAX_ETAG_CHARS


def test_vcf_import_destination_reuses_shared_resource_bound() -> None:
    schema = VcfImportRequest.model_json_schema()["properties"]["address_book_href"]
    assert schema["minLength"] == 1
    assert schema["maxLength"] == MAX_RESOURCE_HREF_CHARS
