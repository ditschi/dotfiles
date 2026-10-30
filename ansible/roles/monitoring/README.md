# monitoring

Telegraf agent for hosts with the feature `monitoring` (private hosts by default).

- **Install:** `telegraf` from the InfluxData apt source (`repos.influxdata.com/debian`, suite `stable`). The signing key is pinned in `files/influxdata-archive.asc` (fingerprint `24C975CBA61A024EE1B631787C3D57159FC2F927`). A failed install fails the run.
- **Inputs:** the local fragments `files/machine_*.conf`; the names come from `tasks/resolve_monitoring.yml` (hardware, device, features). With `INFLUX_TELEGRAF_CONFIG_BASE` set, the remote configs `<base>/<name>` replace them: `/etc/default/telegraf` (mode `0600`) sets `TELEGRAF_OPTS` and `INFLUX_TOKEN` for the upstream `telegraf.service`.
- **Interval:** `telegraf.conf` holds the only `[agent]` table; the fragments must not add one (Telegraf warns about overlapping agent tables). `monitoring_interval` sets `interval` from the resolved names: `machine/pi` 60s, else `machine/server` 15s, else `machine/laptop` 30s, else Telegraf's default 10s. With `INFLUX_TELEGRAF_CONFIG_BASE` no interval is written; the remote configs set their own.
- **Output:** `99_output_influx2.conf` (token) or `99_output_influx1.conf` (user/password), `root:telegraf` mode `0640` so the service user can read them, from the Bitwarden item `influxdb-telegraf-write`, which `machine` hands over as extra vars. A run without credentials keeps an existing output.
- **Start:** Telegraf is enabled and started only with an output (an output file or remote configs); without one it is stopped and disabled, so it does not restart in a loop. After the start the role checks that the unit stays active. With the fragment `machine/docker`, `telegraf` joins the group `docker` to read the Docker socket. Containers skip the service steps.

`machine attention` lists a `monitoring` item when Telegraf is not installed, has no output or is not active.
