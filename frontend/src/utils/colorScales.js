import * as d3 from 'd3';

/**
 * Yellow-Orange-Red sequential scale for trading / price data.
 * Higher values appear as deeper reds.
 *
 * @param {[number, number]} domain - [min, max] of the data values.
 * @returns {d3.ScaleSequential}
 */
export function tradingColorScale(domain = [0, 1]) {
  return d3.scaleSequential(d3.interpolateYlOrRd).domain(domain);
}

/**
 * Green-Blue sequential scale for production / yield data.
 * Higher values appear as deeper blues.
 *
 * @param {[number, number]} domain - [min, max] of the data values.
 * @returns {d3.ScaleSequential}
 */
export function productionColorScale(domain = [0, 1]) {
  return d3.scaleSequential(d3.interpolateGnBu).domain(domain);
}

/**
 * Diverging scale for prediction accuracy / error visualisation.
 * Negative = blue, zero = white, positive = red.
 *
 * @param {[number, number]} domain - [min, max] centred around 0.
 * @returns {d3.ScaleDiverging}
 */
export function predictionColorScale(domain = [-1, 0, 1]) {
  return d3.scaleDiverging(d3.interpolateRdBu).domain(domain);
}
