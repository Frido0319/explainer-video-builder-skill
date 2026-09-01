import unittest

import numpy as np

from explainer_video_v2.audio import apply_bgm_outro


class AudioOutroTests(unittest.TestCase):
    def test_bgm_fades_before_silent_tail(self):
        bed = np.ones((12, 2), dtype=np.float32)

        result = apply_bgm_outro(
            bed,
            sample_rate=1,
            fade_seconds=3.0,
            silent_tail_seconds=5.0,
        )

        np.testing.assert_allclose(result[:5], 1.0)
        self.assertGreater(result[5, 0], result[6, 0])
        self.assertGreater(result[6, 0], 0.0)
        np.testing.assert_allclose(result[7:], 0.0)

    def test_silent_tail_setting_does_not_modify_voice_layer(self):
        voice = np.ones((12, 2), dtype=np.float32)
        bed = np.ones((12, 2), dtype=np.float32)

        result = voice + apply_bgm_outro(
            bed,
            sample_rate=1,
            fade_seconds=3.0,
            silent_tail_seconds=5.0,
        )

        np.testing.assert_allclose(result[7:], voice[7:])


if __name__ == "__main__":
    unittest.main()
