from progress_bar import ProgressBar


def test_init():
    pb = ProgressBar()
    assert pb.width == 20
    assert pb.progress_symbol == "▓"
    assert pb.empty_symbol == "░"

    pb = ProgressBar(width=10, progress_symbol="=", empty_symbol="-")
    assert pb.width == 10
    assert pb.progress_symbol == "="
    assert pb.empty_symbol == "-"


def test_update():
    pb = ProgressBar()

    progress_0 = pb.update(0)
    assert progress_0 == "░░░░░░░░░░░░░░░░░░░░ 0%"

    progress_50 = pb.update(50)
    assert progress_50 == "▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ 50%"

    progress_100 = pb.update(100)
    assert progress_100 == "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100%"
