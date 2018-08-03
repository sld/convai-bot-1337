import requests


def test_request():
    text = 'I am the begt spell cherken!'
    res = requests.post(
        "http://0.0.0.0:3050/respond",
        json={"sentences": text}
    )

    assert res.status_code == 200

    print('original text: {}'.format(text))
    print('corrected text: {}'.format(res.json()['message']))

    return res


if __name__ == '__main__':
    test_request()
