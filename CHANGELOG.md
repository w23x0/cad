# Changelog

## 2026-10-27

- bench: 22 golden parts (44 dual-kernel implementations), all passing with
  volume/bbox/centroid(/interference) contracts, max relative error < 1e-6.
- verify: centroid + interference metrics added to the contract; white-background
  technical-drawing PNGs.
- fuzz: operator pool upgraded (revolve, split; Cone-degenerate cases removed),
  auto-tagging of divergences (F-1/F-5/NEW); ~1300 cases run across seeds,
  findings FZ-8/9/10.
- FINDINGS: F-1..F-9 + FZ-8/9/10 kernel divergences documented with minimal
  repros and Monte-Carlo arbitration; upstream issue drafts prepared.
- mcp: end-to-end stdio test (37 assertions); CI workflow for the future public repo.

## 2026-10-26

- Initial public-repo-ready state: two-kernel verify harness, MCP server,
  3 seed bench parts (plate, L bracket, flange).
