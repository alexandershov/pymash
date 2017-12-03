from pymash import main


async def test_get_game(test_client):
    text = await _get(test_client, '/game')
    assert text == 'hello!'


async def _get(test_client, path):
    app = main.create_app()
    client = await test_client(app)
    resp = await client.get(path)
    text = await resp.text()
    return text
