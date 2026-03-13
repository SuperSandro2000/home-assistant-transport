import { LitElement, html, css, nothing } from "lit";

class DresdenTransportCard extends LitElement {
    static get properties() {
    return {
      hass: {},
      config: {}
    };
  }

  getDepatures() {
    const maxEntries = this.config.max_entries || 10;
    const allDepartures = [];

    for (const ent of this.config.entities) {
      const stateObj = this.hass.states[ent];
      if (stateObj) {
        allDepartures.push(...stateObj.attributes.departures);
      } else {
        throw new Error(`Entity ${ent} not found.`);
      }
    }

    allDepartures.sort((a, b) => a.time.localeCompare(b.time));

    return allDepartures.slice(0, maxEntries);
  }

  render() {
    const maxEntries = this.config.max_entries || 10;
    return html`
    <ha-card><div class="container">
    ${this.getDepatures().map(departure => {
      return html`
        <div class="departures">
          <div class="departure">
            <div class="line">
              <div class="line-icon" style="background-color: ${departure.color}">${departure.line_name}</div>
              <div class="line-pl">${departure.platform}</div>
            </div>
            <div class="direction">${departure.direction}</div>
            <div class="time-slot">
              ${this.config.show_gap
                ? html`<div class="todeparture">(+${departure.gap})</div>`
                : nothing
              }
              <div class="time">${departure.time}</div>
            </div>
          </div>
        </div>
      `;
    })}
    </div></ha-card>
    `;
  }

  setConfig(config) {
    if (!config.entities) {
      throw new Error("You need to define entities");
    }
    this.config = config;
  }

  getCardSize() {
    return 5;
  }

  static get styles() {
    return css`
        .container {
            padding: 10px;
            font-size: 130%;
            display: flex;
            flex-direction: column;
        }
        .stop {
            opacity: 0.6;
            font-weight: 400;
            width: 100%;
            text-align: left;
            padding: 10px 10px 5px 5px;
        }
        .departures {
            width: 100%;
            font-weight: 400;
            line-height: 1.5em;
            display: flex;
            flex-direction: column;
        }
        .departure {
            padding-top: 10px;
            min-height: 40px;
            display: flex;
            flex-wrap: nowrap;
            align-items: center;
            gap: 15px;
        }
        .line {
            min-width: 70px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 5px;
        }
        .line-icon {
            display: inline-block;
            border-radius: 20px;
            padding: 7px 10px 5px;
            font-size: 120%;
            font-weight: 700;
            line-height: 1em;
            color: #FFFFFF;
            text-align: center;
            flex: 1;
        }
        .line-pl {
            border-radius: 5px;
            padding: 5px;
            font-size: 60%;
            font-weight: 600;
            line-height: 1em;
            color: #FFFFFF;
            text-align: center;
            background-color: gray;
        }
        .direction {
            align-self: center;
            flex-grow: 1;
        }
        .time {
            align-self: flex-start;
            font-weight: 700;
            padding-right: 0px;
        }
        .todeparture {
            font-size: 12px;
        }
        .time-slot {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 5px;
        }
    `;
  }
}
customElements.define("dresden-transport-card", DresdenTransportCard);
