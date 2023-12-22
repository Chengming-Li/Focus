# Run "docker exec -it focus-backend-1 pytest" in terminal to test

def test_host_room(app):
    client = app[1]
    client.emit('host', {'ID': "11002331"})
    response = client.get_received()
    assert len(response) == 1, "Invalid number of messages received"
    data = response[0]
    assert data["name"] == "host" and data["args"][0], "invalid host data"

def test_join_leave_room(app):
    client1 = app[1]
    client2 = app[2]
    client1.emit('join', {"room": "Test", 'ID': "11002331"})
    response1 = client1.get_received()
    response2 = client2.get_received()
    assert len(response1) == 1, "Invalid number of messages received"
    assert len(response2) == 0, "Invalid number of messages received"
    client2.emit('join', {"room": "Test", 'ID': "11002330"})
    response1 = client1.get_received()
    response2 = client2.get_received()
    assert len(response1) == len(response2) == 1, "Invalid number of messages received"
    assert response1[0]['args'][0]["userID"] == "11002330", "Client2 joining room failed to notify client1"
    client1.emit('leave')
    response2 = client2.get_received()
    assert len(response2) == 1, "Invalid number of messages received"
    assert response2[0]['name'] == 'leave' and response2[0]['args'][0] == '11002331', "Client2 was not correctly notified of client1's departure"

def test_start_stop_interval(app):
    try:
        client1 = app[1]
        client2 = app[2]
        client1.emit('join', {"room": "Test", 'ID': "928024115890290689"})
        client2.emit('join', {"room": "Test", 'ID': "11002330"})
        response1 = client1.get_received()
        response2 = client2.get_received()
        client1.emit('start_interval', {"name": "Test Interval", "project_id": None})
        response1 = client1.get_received()
        response2 = client2.get_received()
        assert len(response1) == 0, "Interval failed to start"
        assert len(response2) == 1, "Invalid number of messages received"
        data = response2[0]['args'][0]
        intervalID = data["interval_id"]
        assert response2[0]["name"] == "start" and data["userID"] == "928024115890290689" and intervalID, "Client2 was not notified of client1's interval"
        client1.emit('stop_interval')
        response1 = client1.get_received()
        response2 = client2.get_received()
        assert len(response1) == 0, "Interval failed to stop"
        assert len(response2) == 1, "Invalid number of messages received"
        data = response2[0]['args'][0]
        assert response2[0]["name"] == "stop" and data["userID"] == "928024115890290689" and data["interval_id"] == intervalID and data["start_time"] and data["end_time"] and data["name"], "Client2 was not notified of client1's interval"
    finally:
        client = app[0].test_client()
        assert client.delete("/api/interval/" + data["interval_id"]).status_code == 200

def test_fetching_multiple_user_data(app):
    try:
        ids = []
        client = app[0].test_client()
        response = client.post("/api/user", json={
            "username" : "Test1",
            "email" : "test1@gmail.com",
            "timezone" : "America/Los_Angeles",
            "profile_picture" : None
        })
        ids.append(response.get_json().get("id"))
        response = client.post("/api/user", json={
            "username" : "Test2",
            "email" : "test2@gmail.com",
            "timezone" : "America/Los_Angeles",
            "profile_picture" : None
        })
        ids.append(response.get_json().get("id"))
        response = client.post("/api/user", json={
            "username" : "Test3",
            "email" : "test3@gmail.com",
            "timezone" : "America/Los_Angeles",
            "profile_picture" : None
        })
        ids.append(response.get_json().get("id"))
        idString = ", ".join(ids)
        response = client.get(f"/api/users/{idString}")
        assert len(response.get_json()["users"]) == 3, "Invalid response"
    finally:
        # clean up
        for i in ids:
            assert client.delete("/api/user/" + i).status_code == 200

def test_edit_interval(app):
    try:
        client1 = app[1]
        client2 = app[2]
        client1.emit('join', {"room": "Test", 'ID': "928024115890290689"})
        client2.emit('join', {"room": "Test", 'ID': "11002330"})
        client1.emit('start_interval', {"name": "Test Interval", "project_id": None})
        response1 = client1.get_received()
        response2 = client2.get_received()
        client1.emit('edit_interval', {"name": "Test Interval2", "project_id": None})
        response1 = client1.get_received()
        response2 = client2.get_received()
        assert len(response1) == 0, "Failed to edit interval"
        assert len(response2) == 1, "Invalid number of messages received"
        data = response2[0]['args'][0]
        assert response2[0]["name"] == "edit" and data["userID"] == "928024115890290689" and data["interval_name"] == "Test Interval2", "Client2 was not notified of client1's interval"
    finally:
        client = app[0].test_client()
        assert client.delete("/api/interval/" + data["interval_id"]).status_code == 200

