# shop

Small order-processing package. Run the tests with:

    python3 -m unittest discover -s tests

CLI: `python3 -m shop report data/orders.csv`

The CLI streams large files (`shop/stream_report.py`) instead of loading them whole.
