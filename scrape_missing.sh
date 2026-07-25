#!/usr/bin/env bash
# Re-scrape only the pages we don't have yet, in small throttled batches
cd "$(dirname "$0")"
mapfile -t ALL < data/master_urls.txt

todo=()
for u in "${ALL[@]}"; do
  page="${u#https://wiki.walkscape.app/wiki/}"
  f=".firecrawl/wiki.walkscape.app-wiki-${page}.md"
  if [[ ! -s "$f" ]]; then
    todo+=("$u")
  fi
done

echo "Missing: ${#todo[@]} pages"
batch=8
i=0
while (( i < ${#todo[@]} )); do
  chunk=("${todo[@]:i:batch}")
  echo "--- batch $((i/batch+1)): ${#chunk[@]} urls ---"
  firecrawl scrape "${chunk[@]}" >/dev/null 2>&1
  i=$(( i + batch ))
  sleep 12
done
echo "Done. Total cached: $(ls .firecrawl/*.md | wc -l)"
