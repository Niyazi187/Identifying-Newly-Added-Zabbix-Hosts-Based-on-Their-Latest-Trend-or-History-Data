# Identifying-Newly-Added-Zabbix-Hosts-Based-on-Their-Latest-Trend-or-History-Data

This report identifies the oldest available trend or history data for each host to estimate when it was first monitored in Zabbix, without requiring API access to the audit log, which is restricted to Super Admins.

When a host is onboarded for monitoring, it is initially assigned to a designated PreProd host group. This allows the team to verify that the Zabbix agent is responding and that items and triggers are functioning correctly before the host is released to Production and handed over to the operations team.

The report provides an estimate of how long each host has been in PreProd, helping the team track onboarding progress and identify hosts that have remained in the testing environment for too long.