"""Allow running the tool as `python -m mail_merge`."""

import sys

from mail_merge.cli import main

sys.exit(main())
