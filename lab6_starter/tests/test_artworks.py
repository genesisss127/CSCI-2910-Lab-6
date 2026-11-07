import pytest

def test_get_seeded_artwork(client, seeded_db):
    # Arrange: seeded_db has already loaded the 11 artworks (the Mona Lisa is first)
    expected = {"id": 1, **seeded_db[0]}

    # Act
    response = client.get("/artworks/1")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected

def test_list_artworks_empty(client):
    # With no seed data (notice we don't ask for seeded_db), GET /artworks/ returns 200 and an empty list
    response = client.get("/artworks/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_seeded_artwork(client, seeded_db):
    # seeded_db has already loaded the 11 artworks (the Mona Lisa is first)
    expected = {"id": 1, **seeded_db[0]}
    response = client.get("/artworks/1")
    assert response.status_code == 200
    assert response.json() == expected


def test_create_artwork(client, sample_artwork):
    response = client.post("/artworks/", json=sample_artwork)
    assert response.status_code == 201
    
    data = response.json()
    assert isinstance(data.get("id"), int)
    
    # Assert every other field matches what was sent
    for key, value in sample_artwork.items():
        assert data[key] == value


def test_create_artwork_is_saved(client, created_artwork):
    artwork_id = created_artwork["id"]
    response = client.get(f"/artworks/{artwork_id}")
    assert response.status_code == 200
    assert response.json() == created_artwork


def test_update_artwork(client, created_artwork, updated_artwork):
    artwork_id = created_artwork["id"]
    response = client.put(f"/artworks/{artwork_id}", json=updated_artwork)
    
    assert response.status_code == 200
    expected_response = {"id": artwork_id, **updated_artwork}
    assert response.json() == expected_response
    
    # Check that the change was actually saved in the database, not just echoed back
    get_response = client.get(f"/artworks/{artwork_id}")
    assert get_response.status_code == 200
    assert get_response.json() == expected_response


def test_delete_artwork(client, created_artwork):
    artwork_id = created_artwork["id"]
    response = client.delete(f"/artworks/{artwork_id}")
    
    assert response.status_code == 204
    assert response.content == b""
    
    # GET it again to confirm it is gone
    get_response = client.get(f"/artworks/{artwork_id}")
    assert get_response.status_code == 404

#part 5 unhappy path tests
#artwork not found - 7
@pytest.mark.parametrize(
    "method, use_body",
    [
        ("get", False),
        ("put", True),
        ("delete", False),
    ],
    ids=["get", "put", "delete"],
)
# 7
def test_artwork_not_found(client, sample_artwork, method, use_body):
    kwargs = {"json": sample_artwork} if use_body else {}
    response = client.request(method, "/artworks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}


# 8
def test_non_integer_id(client):
    response = client.get("/artworks/mona-lisa")
    assert response.status_code == 422

# 9
def test_create_duplicate(client, created_artwork):
    duplicate_data = {k: v for k, v in created_artwork.items() if k != "id"}
    response = client.post("/artworks/", json=duplicate_data)
    assert response.status_code == 409
    assert response.json() == {"detail": "An artwork with that title and artist already exists"}

# 10
def test_create_duplicate_ignores_case(client, created_artwork):
    duplicate_data = {
        "title": created_artwork["title"].upper(),
        "artist": created_artwork["artist"].lower(),
        "year": created_artwork["year"],
        "medium": created_artwork["medium"],
        "museum": created_artwork["museum"],
        "image_url": created_artwork["image_url"],
    }
    response = client.post("/artworks/", json=duplicate_data)
    assert response.status_code == 409
    assert response.json() == {"detail": "An artwork with that title and artist already exists"}

# 11
def test_update_into_duplicate(client, seeded_db):
    mona_lisa = seeded_db[0]
    update_data = {
        "title": mona_lisa["title"],
        "artist": mona_lisa["artist"],
        "year": 1489,
        "medium": "Oil on wood",
        "museum": "Czartoryski Museum",
        "image_url": "https://example.com/ermine.jpg",
    }
    response = client.put("/artworks/2", json=update_data)
    assert response.status_code == 409
    
    get_response = client.get("/artworks/2")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Lady with an Ermine"

# 12
def test_update_same_title_and_artist_is_allowed(client, created_artwork):
    update_data = {
        "title": created_artwork["title"],
        "artist": created_artwork["artist"],
        "year": created_artwork["year"],
        "medium": created_artwork["medium"],
        "museum": "A Brand New Museum",
        "image_url": created_artwork["image_url"],
    }
    response = client.put(f"/artworks/{created_artwork['id']}", json=update_data)
    assert response.status_code == 200
    assert response.json()["museum"] == "A Brand New Museum"
 # part 6 parametrize everything else


# 13
@pytest.mark.parametrize(
    "missing_field",
    ["title", "artist", "year", "medium", "museum", "image_url"],
    ids=["missing-title", "missing-artist", "missing-year", "missing-medium", "missing-museum", "missing-image_url"]
)
def test_create_missing_field(client, sample_artwork, missing_field):
    bad_data = sample_artwork.copy()
    del bad_data[missing_field]
    response = client.post("/artworks/", json=bad_data)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing_field]


#14
@pytest.mark.parametrize(
    "bad_key, bad_value",
    [
        ("year", 3000),
        ("year", "nineteen-oh-seven"),
        ("title", ""),
    ],
    ids=["future-year", "year-not-int", "empty-title"]
)
def test_create_invalid_value(client, sample_artwork, bad_key, bad_value):
    bad_data = sample_artwork.copy()
    bad_data[bad_key] = bad_value
    response = client.post("/artworks/", json=bad_data)
    assert response.status_code == 422

#15
@pytest.mark.parametrize(
    "params, expected_count",
    [
        ({"limit": 3}, 3),
        ({"limit": 0}, 0),
        ({"skip": 5, "limit": 5}, 5),
        ({"skip": 50, "limit": 10}, 0),
    ],
    ids=["limit-3", "limit-0", "skip-5", "skip-past-end"]
)
def test_pagination_counts(client, seeded_db, params, expected_count):
    response = client.get("/artworks/", params=params)
    assert response.status_code == 200
    assert len(response.json()) == expected_count

#16
@pytest.mark.parametrize(
    "bad_params",
    [
        {"limit": -1},
        {"skip": -1},
        {"limit": 200},
    ],
    ids=["negative-limit", "negative-skip", "limit-too-large"]
)
def test_pagination_invalid(client, seeded_db, bad_params):
    response = client.get("/artworks/", params=bad_params)
    assert response.status_code == 422

# 17
@pytest.mark.parametrize(
    "artist_query, expected_titles",
    [
        ("Claude Monet", ["Impression, Sunrise", "Woman with a Parasol – Madame Monet and Her Son"]),
        ("monet", ["Impression, Sunrise", "Woman with a Parasol – Madame Monet and Her Son"]),
        ("da vinci", ["Mona Lisa", "Lady with an Ermine"]),
        ("Nonexistent Artist", []),
    ],
    ids=["exact-full-name", "lowercase-partial", "da-vinci-partial", "no-match"]
)
def test_filter_by_artist(client, seeded_db, artist_query, expected_titles):
    response = client.get("/artworks/", params={"artist": artist_query})
    assert response.status_code == 200
    titles = [art["title"] for art in response.json()]
    assert titles == expected_titles

#part 7 would your tests catch a bug
