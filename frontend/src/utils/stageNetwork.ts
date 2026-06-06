import type { PlayCleaned, PlayNetwork } from '@/types'

export function speakersInBlockRange(
  play: PlayCleaned,
  range: [number, number],
): Set<string> {
  const ids = new Set<string>()
  for (const b of play.blocks ?? []) {
    if (b.block_index >= range[0] && b.block_index <= range[1] && b.speaker_id) {
      ids.add(b.speaker_id)
    }
  }
  return ids
}

export function filterNetworkBySpeakers(
  net: PlayNetwork,
  activeIds: Set<string>,
): { nodes: PlayNetwork['nodes']; links: PlayNetwork['links'] } {
  if (!activeIds.size) {
    return { nodes: net.nodes, links: net.links }
  }
  const nodes = net.nodes.filter((n) => activeIds.has(n.id))
  const idSet = new Set(nodes.map((n) => n.id))
  const links = net.links.filter((l) => idSet.has(l.source) && idSet.has(l.target))
  return { nodes, links }
}

export function buildStageSubgraph(
  play: PlayCleaned,
  net: PlayNetwork,
  blockRange: [number, number],
): { nodes: PlayNetwork['nodes']; links: PlayNetwork['links'] } {
  const speakers = speakersInBlockRange(play, blockRange)
  return filterNetworkBySpeakers(net, speakers)
}
