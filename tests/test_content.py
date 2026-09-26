from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.validate_content import validate_links


class ContentLinkTests(unittest.TestCase):
    def test_nested_documentation_links_are_checked(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Workshop\n", encoding="utf-8")
            nested = root / "docs" / "codespaces"
            nested.mkdir(parents=True)
            guide = nested / "README.md"
            guide.write_text("[Image](IMAGE.md)\n", encoding="utf-8")

            errors = []
            validate_links(root, errors)
            self.assertEqual(
                errors,
                ["docs/codespaces/README.md: broken link 'IMAGE.md'"],
            )

            (nested / "IMAGE.md").write_text("# Image\n", encoding="utf-8")
            errors = []
            validate_links(root, errors)
            self.assertEqual(errors, [])
