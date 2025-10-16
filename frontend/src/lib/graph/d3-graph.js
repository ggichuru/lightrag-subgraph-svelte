import * as d3 from 'd3';

function applyZoom(svg, container) {
  const zoom = d3.zoom().scaleExtent([0.2, 4]).on('zoom', (event) => {
    container.attr('transform', event.transform);
  });
  svg.call(zoom);
}

export function createGraph(svgElement, data, options = {}) {
  const width = options.width ?? svgElement.clientWidth ?? 800;
  const height = options.height ?? svgElement.clientHeight ?? 600;

  const svg = d3.select(svgElement);
  svg.selectAll('*').remove();
  svg.attr('viewBox', [0, 0, width, height]);

  const container = svg.append('g');
  applyZoom(svg, container);

  const linkGroup = container.append('g').attr('class', 'links');
  const nodeGroup = container.append('g').attr('class', 'nodes');

  const simulation = d3
    .forceSimulation()
    .force(
      'link',
      d3.forceLink().id((d) => d.id).distance((d) => 80 + (d.weight ?? 0) * 20)
    )
    .force('charge', d3.forceManyBody().strength(-220))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius((d) => (d.size ?? 8) + 4))
    .alphaDecay(0.02);

  function updateGraph(newData) {
    const links = linkGroup.selectAll('line').data(newData.links, (d) => `${d.source}-${d.target}`);

    links
      .join(
        (enter) =>
          enter
            .append('line')
            .attr('stroke', '#64748b')
            .attr('stroke-width', (d) => Math.max(1, d.weight ?? 1))
            .attr('stroke-opacity', 0.6),
        (update) => update,
        (exit) => exit.transition().duration(300).style('opacity', 0).remove()
      );

    const nodes = nodeGroup.selectAll('g').data(newData.nodes, (d) => d.id);

    const nodesEnter = nodes
      .enter()
      .append('g')
      .attr('class', 'node')
      .call(
        d3
          .drag()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    nodesEnter
      .append('circle')
      .attr('r', (d) => d.size ?? 8)
      .attr('fill', (d) => d.color ?? '#38bdf8')
      .attr('stroke', (d) => (d.is_focal ? '#facc15' : '#0f172a'))
      .attr('stroke-width', (d) => (d.is_focal ? 2 : 1.2))
      .attr('opacity', (d) => (d.is_focal ? 1 : 0.85));

    nodesEnter
      .append('text')
      .text((d) => d.label)
      .attr('x', 0)
      .attr('y', (d) => (d.size ?? 8) + 12)
      .attr('text-anchor', 'middle')
      .attr('fill', '#e2e8f0')
      .attr('font-size', 12)
      .attr('stroke', '#0f172a')
      .attr('stroke-width', 0.25);

    nodes
      .select('circle')
      .transition()
      .duration(500)
      .attr('r', (d) => d.size ?? 8)
      .attr('fill', (d) => d.color ?? '#38bdf8')
      .attr('stroke', (d) => (d.is_focal ? '#facc15' : '#0f172a'))
      .attr('stroke-width', (d) => (d.is_focal ? 2 : 1.2));

    nodes
      .select('text')
      .text((d) => d.label)
      .attr('y', (d) => (d.size ?? 8) + 12);

    nodes.exit().transition().duration(300).style('opacity', 0).remove();

    simulation.nodes(newData.nodes);
    simulation.force('link').links(newData.links);
    simulation.alpha(0.8).restart();

    simulation.on('tick', () => {
      linkGroup
        .selectAll('line')
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);

      nodeGroup
        .selectAll('g')
        .attr('transform', (d) => `translate(${d.x}, ${d.y})`);
    });
  }

  updateGraph(data);

  return {
    simulation,
    update: updateGraph,
    destroy() {
      simulation.stop();
      svg.selectAll('*').remove();
    }
  };
}

export function updateGraph(instance, data) {
  if (instance) {
    instance.update(data);
  }
}

export function destroyGraph(instance) {
  if (instance && typeof instance.destroy === 'function') {
    instance.destroy();
  }
}
