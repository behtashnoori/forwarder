import unittest

from scan_repository_secrets import iter_batch_blobs


class BatchParserTests(unittest.TestCase):
    def test_non_blob_payload_is_consumed_before_next_blob(self):
        objects = {
            "a" * 40: {"tree-path"},
            "b" * 40: {"safe.txt"},
        }
        batch = (
            f"{'a' * 40} tree 4\nTREE\n".encode()
            + f"{'b' * 40} blob 4\nSAFE\n".encode()
        )

        self.assertEqual(
            iter_batch_blobs(batch, objects),
            [("b" * 40, {"safe.txt"}, b"SAFE")],
        )

    def test_truncated_payload_fails_closed(self):
        objects = {"c" * 40: {"safe.txt"}}
        batch = f"{'c' * 40} blob 5\nDATA\n".encode()

        with self.assertRaisesRegex(RuntimeError, "Truncated cat-file payload"):
            iter_batch_blobs(batch, objects)


if __name__ == "__main__":
    unittest.main()
