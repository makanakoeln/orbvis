/**
 * OrbVis-specific implementation of cmk-frontend-vue's
 * ``components/CmkIcon/icons.constants.ts``.
 *
 * Holds icon paths as plain strings (e.g. ``themes/facelift/images/icon_x.svg``)
 * rather than the upstream's ``~cmk-frontend/themes/...?url&no-inline`` Vite
 * asset imports. The path is concatenated with a runtime ``checkmkBase()``
 * prefix in ``utils.ts``, so icons are loaded from the sibling Checkmk site
 * at request time and the bundle has zero asset deps.
 *
 * Wired in via ``CMK_STUBS`` in ``frontend/vite.config.ts`` so the vendored
 * CmkIcon files stay byte-identical to upstream.
 */
import { cva } from 'class-variance-authority';
import { type IconNames, type IconSizes } from 'cmk-shared-typing/typescript/icon';

const lightAssumeBgPng = 'themes/facelift/images/assume_bg.png';
const lightCheckboxHoverBgPng = 'themes/facelift/images/checkbox_hover_bg.png';
const lightDashletAnchorSvg = 'themes/facelift/images/dashlet_anchor.svg';
const lightDashletCloneSvg = 'themes/facelift/images/dashlet_clone.svg';
const lightDashletDeleteSvg = 'themes/facelift/images/dashlet_delete.svg';
const lightDashletEditSvg = 'themes/facelift/images/dashlet_edit.svg';
const lightDashletResizeSvg = 'themes/facelift/images/dashlet_resize.svg';
const lightFaviconIco = 'themes/facelift/images/favicon.ico';
const lightFolderClosedPng = 'themes/facelift/images/folder_closed.png';
const lightFolderHiPng = 'themes/facelift/images/folder_hi.png';
const lightFolderOpenPng = 'themes/facelift/images/folder_open.png';
const lightGlobePng = 'themes/facelift/images/globe.png';
const lightIcon2faSvg = 'themes/facelift/images/icon_2fa.svg';
const lightIcon2faBackupCodesSvg = 'themes/facelift/images/icon_2fa_backup_codes.svg';
const lightIconAbortPng = 'themes/facelift/images/icon_abort.png';
const lightIconAboutCheckmkSvg = 'themes/facelift/images/icon_about_checkmk.svg';
const lightIconAcceptSvg = 'themes/facelift/images/icon_accept.svg';
const lightIconAcceptAllSvg = 'themes/facelift/images/icon_accept_all.svg';
const lightIconAckPng = 'themes/facelift/images/icon_ack.png';
const lightIconAcknowledgeTestPng = 'themes/facelift/images/icon_acknowledge_test.png';
const lightIconActionPng = 'themes/facelift/images/icon_action.png';
const lightIconActivatePng = 'themes/facelift/images/icon_activate.png';
const lightIconAddPng = 'themes/facelift/images/icon_add.png';
const lightIconAddDashletPng = 'themes/facelift/images/icon_add_dashlet.png';
const lightIconAddRuleSvg = 'themes/facelift/images/icon_add_rule.svg';
const lightIconAgentOutputPng = 'themes/facelift/images/icon_agent_output.png';
const lightIconAgentRegistrationSvg = 'themes/facelift/images/icon_agent_registration.svg';
const lightIconAgentsSvg = 'themes/facelift/images/icon_agents.svg';
const lightIconAggrSvg = 'themes/facelift/images/icon_aggr.svg';
const lightIconAggrSingleSvg = 'themes/facelift/images/icon_aggr_single.svg';
const lightIconAggrSingleProblemSvg = 'themes/facelift/images/icon_aggr_single_problem.svg';
const lightIconAggrcompPng = 'themes/facelift/images/icon_aggrcomp.png';
const lightIconAixTgzSvg = 'themes/facelift/images/icon_aix_tgz.svg';
const lightIconAlertPng = 'themes/facelift/images/icon_alert.png';
const lightIconAlertAckPng = 'themes/facelift/images/icon_alert_ack.png';
const lightIconAlertAckstopPng = 'themes/facelift/images/icon_alert_ackstop.png';
const lightIconAlertAlertHandlerFailedPng =
    'themes/facelift/images/icon_alert_alert_handler_failed.png';
const lightIconAlertAlertHandlerStartedPng =
    'themes/facelift/images/icon_alert_alert_handler_started.png';
const lightIconAlertAlertHandlerStoppedPng =
    'themes/facelift/images/icon_alert_alert_handler_stopped.png';
const lightIconAlertCmkNotifyPng = 'themes/facelift/images/icon_alert_cmk_notify.png';
const lightIconAlertCommandPng = 'themes/facelift/images/icon_alert_command.png';
const lightIconAlertCritSvg = 'themes/facelift/images/icon_alert_crit.svg';
const lightIconAlertDownPng = 'themes/facelift/images/icon_alert_down.png';
const lightIconAlertDowntimePng = 'themes/facelift/images/icon_alert_downtime.png';
const lightIconAlertDowntimestopPng = 'themes/facelift/images/icon_alert_downtimestop.png';
const lightIconAlertFlappingPng = 'themes/facelift/images/icon_alert_flapping.png';
const lightIconAlertHandlersSvg = 'themes/facelift/images/icon_alert_handlers.svg';
const lightIconAlertNotifyPng = 'themes/facelift/images/icon_alert_notify.png';
const lightIconAlertNotifyProgressPng = 'themes/facelift/images/icon_alert_notify_progress.png';
const lightIconAlertNotifyResultPng = 'themes/facelift/images/icon_alert_notify_result.png';
const lightIconAlertOkPng = 'themes/facelift/images/icon_alert_ok.png';
const lightIconAlertReloadPng = 'themes/facelift/images/icon_alert_reload.png';
const lightIconAlertRestartPng = 'themes/facelift/images/icon_alert_restart.png';
const lightIconAlertStartPng = 'themes/facelift/images/icon_alert_start.png';
const lightIconAlertStopPng = 'themes/facelift/images/icon_alert_stop.png';
const lightIconAlertTimelineSvg = 'themes/facelift/images/icon_alert_timeline.svg';
const lightIconAlertUnknownPng = 'themes/facelift/images/icon_alert_unknown.png';
const lightIconAlertUnreachPng = 'themes/facelift/images/icon_alert_unreach.png';
const lightIconAlertUpPng = 'themes/facelift/images/icon_alert_up.png';
const lightIconAlertWarnPng = 'themes/facelift/images/icon_alert_warn.png';
const lightIconAlertOverviewSvg = 'themes/facelift/images/icon_alert-overview.svg';
const lightIconAlertsSvg = 'themes/facelift/images/icon_alerts.svg';
const lightIconAllStatesPng = 'themes/facelift/images/icon_all_states.png';
const lightIconAnalysisSvg = 'themes/facelift/images/icon_analysis.svg';
const lightIconAnalyzeSvg = 'themes/facelift/images/icon_analyze.svg';
const lightIconAnalyzeConfigSvg = 'themes/facelift/images/icon_analyze_config.svg';
const lightIconAnnotationPng = 'themes/facelift/images/icon_annotation.png';
const lightIconApiSvg = 'themes/facelift/images/icon_api.svg';
const lightIconAppMonitoringTopicSvg = 'themes/facelift/images/icon_app_monitoring_topic.svg';
const lightIconApplyPng = 'themes/facelift/images/icon_apply.png';
const lightIconArSimulatePng = 'themes/facelift/images/icon_ar_simulate.png';
const lightIconArchiveEventPng = 'themes/facelift/images/icon_archive_event.png';
const lightIconAssignSvg = 'themes/facelift/images/icon_assign.svg';
const lightIconAssume0Png = 'themes/facelift/images/icon_assume_0.png';
const lightIconAssume1Png = 'themes/facelift/images/icon_assume_1.png';
const lightIconAssume2Png = 'themes/facelift/images/icon_assume_2.png';
const lightIconAssume3Png = 'themes/facelift/images/icon_assume_3.png';
const lightIconAssumeNonePng = 'themes/facelift/images/icon_assume_none.png';
const lightIconAuditlogSvg = 'themes/facelift/images/icon_auditlog.svg';
const lightIconAutherrPng = 'themes/facelift/images/icon_autherr.png';
const lightIconAuthokPng = 'themes/facelift/images/icon_authok.png';
const lightIconAvComputationPng = 'themes/facelift/images/icon_av_computation.png';
const lightIconAvailabilitySvg = 'themes/facelift/images/icon_availability.svg';
const lightIconAwsSvg = 'themes/facelift/images/icon_aws.svg';
const lightIconAwsLogoSvg = 'themes/facelift/images/icon_aws_logo.svg';
const lightIconAzureStorageSvg = 'themes/facelift/images/icon_azure_storage.svg';
const lightIconAzureVmsSvg = 'themes/facelift/images/icon_azure_vms.svg';
const lightIconBackPng = 'themes/facelift/images/icon_back.png';
const lightIconBackOffPng = 'themes/facelift/images/icon_back_off.png';
const lightIconBackgroundJobDetailsPng = 'themes/facelift/images/icon_background_job_details.png';
const lightIconBackgroundJobsSvg = 'themes/facelift/images/icon_background_jobs.svg';
const lightIconBackupSvg = 'themes/facelift/images/icon_backup.svg';
const lightIconBackupRestoreStopPng = 'themes/facelift/images/icon_backup_restore_stop.png';
const lightIconBackupStartPng = 'themes/facelift/images/icon_backup_start.png';
const lightIconBackupStatePng = 'themes/facelift/images/icon_backup_state.png';
const lightIconBackupStopPng = 'themes/facelift/images/icon_backup_stop.png';
const lightIconBackupTargetEditPng = 'themes/facelift/images/icon_backup_target_edit.png';
const lightIconBackupTargetsSvg = 'themes/facelift/images/icon_backup_targets.svg';
const lightIconBakeSvg = 'themes/facelift/images/icon_bake.svg';
const lightIconBakeResultPng = 'themes/facelift/images/icon_bake_result.png';
const lightIconBarplotSvg = 'themes/facelift/images/icon_barplot.svg';
const lightIconBiFreezeSvg = 'themes/facelift/images/icon_bi_freeze.svg';
const lightIconBilistPng = 'themes/facelift/images/icon_bilist.png';
const lightIconBitreePng = 'themes/facelift/images/icon_bitree.png';
const lightIconBookmarkListSvg = 'themes/facelift/images/icon_bookmark_list.svg';
const lightIconBottomPng = 'themes/facelift/images/icon_bottom.png';
const lightIconBulkSvg = 'themes/facelift/images/icon_bulk.svg';
const lightIconBulkImportPng = 'themes/facelift/images/icon_bulk_import.png';
const lightIconCachedPng = 'themes/facelift/images/icon_cached.png';
const lightIconCancelSvg = 'themes/facelift/images/icon_cancel.svg';
const lightIconCancelNotificationsSvg = 'themes/facelift/images/icon_cancel_notifications.svg';
const lightIconCannotReschedulePng = 'themes/facelift/images/icon_cannot_reschedule.png';
const lightIconCertificateSvg = 'themes/facelift/images/icon_certificate.svg';
const lightIconCheckSvg = 'themes/facelift/images/icon_check.svg';
const lightIconCheckParametersSvg = 'themes/facelift/images/icon_check_parameters.svg';
const lightIconCheckPluginsSvg = 'themes/facelift/images/icon_check_plugins.svg';
const lightIconCheckboxSvg = 'themes/facelift/images/icon_checkbox.svg';
const lightIconCheckmarkSvg = 'themes/facelift/images/icon_checkmark.svg';
const lightIconCheckmarkBareSvg = 'themes/facelift/images/icon_checkmark_bare.svg';
const lightIconCheckmarkBgWhiteSvg = 'themes/facelift/images/icon_checkmark_bg_white.svg';
const lightIconCheckmarkOrangeSvg = 'themes/facelift/images/icon_checkmark_orange.svg';
const lightIconCheckmarkPlusSvg = 'themes/facelift/images/icon_checkmark_plus.svg';
const lightIconCheckmkSvg = 'themes/facelift/images/icon_checkmk.svg';
const lightIconCheckmkLogoSvg = 'themes/facelift/images/icon_checkmk_logo.svg';
const lightIconCheckmkLogoMinSvg = 'themes/facelift/images/icon_checkmk_logo_min.svg';
const lightIconCleanupPng = 'themes/facelift/images/icon_cleanup.png';
const lightIconClearPng = 'themes/facelift/images/icon_clear.png';
const lightIconClipboardSvg = 'themes/facelift/images/icon_clipboard.svg';
const lightIconClockSvg = 'themes/facelift/images/icon_clock.svg';
const lightIconCloneSvg = 'themes/facelift/images/icon_clone.svg';
const lightIconCloseSvg = 'themes/facelift/images/icon_close.svg';
const lightIconClosetimewarpPng = 'themes/facelift/images/icon_closetimewarp.png';
const lightIconCloudSvg = 'themes/facelift/images/icon_cloud.svg';
const lightIconClusterPng = 'themes/facelift/images/icon_cluster.png';
const lightIconCollapsePng = 'themes/facelift/images/icon_collapse.png';
const lightIconCollapseArrowPng = 'themes/facelift/images/icon_collapse_arrow.png';
const lightIconColorModeSvg = 'themes/facelift/images/icon_color_mode.svg';
const lightIconCommandsSvg = 'themes/facelift/images/icon_commands.svg';
const lightIconCommentSvg = 'themes/facelift/images/icon_comment.svg';
const lightIconConditionPng = 'themes/facelift/images/icon_condition.png';
const lightIconConfigurationSvg = 'themes/facelift/images/icon_configuration.svg';
const lightIconConnectionTestsSvg = 'themes/facelift/images/icon_connection_tests.svg';
const lightIconContactgroupsSvg = 'themes/facelift/images/icon_contactgroups.svg';
const lightIconContinuePng = 'themes/facelift/images/icon_continue.png';
const lightIconCopiedSvg = 'themes/facelift/images/icon_copied.svg';
const lightIconCountingPng = 'themes/facelift/images/icon_counting.png';
const lightIconCrashSvg = 'themes/facelift/images/icon_crash.svg';
const lightIconCrashGlowPng = 'themes/facelift/images/icon_crash_glow.png';
const lightIconCritProblemSvg = 'themes/facelift/images/icon_crit_problem.svg';
const lightIconCriticalPng = 'themes/facelift/images/icon_critical.png';
const lightIconCrossSvg = 'themes/facelift/images/icon_cross.svg';
const lightIconCrossBgWhiteSvg = 'themes/facelift/images/icon_cross_bg_white.svg';
const lightIconCrossGreySvg = 'themes/facelift/images/icon_cross_grey.svg';
const lightIconCustomAttrSvg = 'themes/facelift/images/icon_custom_attr.svg';
const lightIconCustomGraphPng = 'themes/facelift/images/icon_custom_graph.png';
const lightIconCustomSnapinSvg = 'themes/facelift/images/icon_custom_snapin.svg';
const lightIconCustomerManagementPng = 'themes/facelift/images/icon_customer_management.png';
const lightIconD146n0571c5Png = 'themes/facelift/images/icon_d146n0571c5.png';
const lightIconDashSvg = 'themes/facelift/images/icon_dash.svg';
const lightIconDashboardSvg = 'themes/facelift/images/icon_dashboard.svg';
const lightIconDashboardControlsPng = 'themes/facelift/images/icon_dashboard_controls.png';
const lightIconDashboardEditSvg = 'themes/facelift/images/icon_dashboard_edit.svg';
const lightIconDashboardGridSvg = 'themes/facelift/images/icon_dashboard_grid.svg';
const lightIconDashboardMainSvg = 'themes/facelift/images/icon_dashboard_main.svg';
const lightIconDashboardMenuarrowSvg = 'themes/facelift/images/icon_dashboard_menuarrow.svg';
const lightIconDashboardProblemsSvg = 'themes/facelift/images/icon_dashboard_problems.svg';
const lightIconDashboardSystemSvg = 'themes/facelift/images/icon_dashboard_system.svg';
const lightIconDashletNetworkTopologyPng =
    'themes/facelift/images/icon_dashlet_network_topology.png';
const lightIconDashletNodataPng = 'themes/facelift/images/icon_dashlet_nodata.png';
const lightIconDashletNotificationsBarChartPng =
    'themes/facelift/images/icon_dashlet_notifications_bar_chart.png';
const lightIconDashletUrlPng = 'themes/facelift/images/icon_dashlet_url.png';
const lightIconDcdConnectionsSvg = 'themes/facelift/images/icon_dcd_connections.svg';
const lightIconDcdExecutePng = 'themes/facelift/images/icon_dcd_execute.png';
const lightIconDcdHistoryPng = 'themes/facelift/images/icon_dcd_history.png';
const lightIconDelayedPng = 'themes/facelift/images/icon_delayed.png';
const lightIconDeleteSvg = 'themes/facelift/images/icon_delete.svg';
const lightIconDeployAgentsPng = 'themes/facelift/images/icon_deploy_agents.png';
const lightIconDeploymentErrorPng = 'themes/facelift/images/icon_deployment_error.png';
const lightIconDeploymentStatusPng = 'themes/facelift/images/icon_deployment_status.png';
const lightIconDerivedDowntimePng = 'themes/facelift/images/icon_derived_downtime.png';
const lightIconDetailPng = 'themes/facelift/images/icon_detail.png';
const lightIconDeveloperResourcesSvg = 'themes/facelift/images/icon_developer_resources.svg';
const lightIconDevelopmentSvg = 'themes/facelift/images/icon_development.svg';
const lightIconDiagnosePng = 'themes/facelift/images/icon_diagnose.png';
const lightIconDiagnosticsSvg = 'themes/facelift/images/icon_diagnostics.svg';
const lightIconDiagnosticsDumpFilePng = 'themes/facelift/images/icon_diagnostics_dump_file.png';
const lightIconDisableTestPng = 'themes/facelift/images/icon_disable_test.png';
const lightIconDisabledSvg = 'themes/facelift/images/icon_disabled.svg';
const lightIconDisabledServiceSvg = 'themes/facelift/images/icon_disabled_service.svg';
const lightIconDissolveOperationPng = 'themes/facelift/images/icon_dissolve_operation.png';
const lightIconDockerSvg = 'themes/facelift/images/icon_docker.svg';
const lightIconDownPng = 'themes/facelift/images/icon_down.png';
const lightIconDownloadPng = 'themes/facelift/images/icon_download.png';
const lightIconDownloadAgentsSvg = 'themes/facelift/images/icon_download_agents.svg';
const lightIconDownloadCsvPng = 'themes/facelift/images/icon_download_csv.png';
const lightIconDownloadJsonPng = 'themes/facelift/images/icon_download_json.png';
const lightIconDowntimeSvg = 'themes/facelift/images/icon_downtime.svg';
const lightIconDowntimeForReportPng = 'themes/facelift/images/icon_downtime_for_report.png';
const lightIconDragSvg = 'themes/facelift/images/icon_drag.svg';
const lightIconEditSvg = 'themes/facelift/images/icon_edit.svg';
const lightIconEditCustomGraphPng = 'themes/facelift/images/icon_edit_custom_graph.png';
const lightIconEditForecastModelPng = 'themes/facelift/images/icon_edit_forecast_model.png';
const lightIconEmailPng = 'themes/facelift/images/icon_email.png';
const lightIconEmptyPng = 'themes/facelift/images/icon_empty.png';
const lightIconEnableTestPng = 'themes/facelift/images/icon_enable_test.png';
const lightIconEnabledPng = 'themes/facelift/images/icon_enabled.png';
const lightIconEncryptedPng = 'themes/facelift/images/icon_encrypted.png';
const lightIconEndPng = 'themes/facelift/images/icon_end.png';
const lightIconErrorPng = 'themes/facelift/images/icon_error.png';
const lightIconEventConsoleStatusSvg = 'themes/facelift/images/icon_event console_status.svg';
const lightIconEventSvg = 'themes/facelift/images/icon_event.svg';
const lightIconEventConsoleSvg = 'themes/facelift/images/icon_event_console.svg';
const lightIconExpandPng = 'themes/facelift/images/icon_expand.png';
const lightIconExportPng = 'themes/facelift/images/icon_export.png';
const lightIconExportLinkSvg = 'themes/facelift/images/icon_export_link.svg';
const lightIconExportRuleSvg = 'themes/facelift/images/icon_export_rule.svg';
const lightIconExternalSvg = 'themes/facelift/images/icon_external.svg';
const lightIconFactoryresetPng = 'themes/facelift/images/icon_factoryreset.png';
const lightIconFakeCheckResultSvg = 'themes/facelift/images/icon_fake_check_result.svg';
const lightIconFavoriteSvg = 'themes/facelift/images/icon_favorite.svg';
const lightIconFilterSvg = 'themes/facelift/images/icon_filter.svg';
const lightIconFilterLineSvg = 'themes/facelift/images/icon_filter_line.svg';
const lightIconFiltersSetPng = 'themes/facelift/images/icon_filters_set.png';
const lightIconFixallSvg = 'themes/facelift/images/icon_fixall.svg';
const lightIconFlappingPng = 'themes/facelift/images/icon_flapping.png';
const lightIconFolderSvg = 'themes/facelift/images/icon_folder.svg';
const lightIconFolderBlueSvg = 'themes/facelift/images/icon_folder_blue.svg';
const lightIconFolderpropertiesPng = 'themes/facelift/images/icon_folderproperties.png';
const lightIconForecastGraphPng = 'themes/facelift/images/icon_forecast_graph.png';
const lightIconForeignChangesPng = 'themes/facelift/images/icon_foreign_changes.png';
const lightIconForthPng = 'themes/facelift/images/icon_forth.png';
const lightIconForthOffPng = 'themes/facelift/images/icon_forth_off.png';
const lightIconFrameurlSvg = 'themes/facelift/images/icon_frameurl.svg';
const lightIconGaugeSvg = 'themes/facelift/images/icon_gauge.svg';
const lightIconGcpSvg = 'themes/facelift/images/icon_gcp.svg';
const lightIconGlobalSettingsSvg = 'themes/facelift/images/icon_global_settings.svg';
const lightIconGraphSvg = 'themes/facelift/images/icon_graph.svg';
const lightIconGraphCollectionPng = 'themes/facelift/images/icon_graph_collection.png';
const lightIconGraphTimeSvg = 'themes/facelift/images/icon_graph_time.svg';
const lightIconGraphTuningPng = 'themes/facelift/images/icon_graph_tuning.png';
const lightIconGuiDesignPng = 'themes/facelift/images/icon_gui_design.png';
const lightIconGuitestPng = 'themes/facelift/images/icon_guitest.png';
const lightIconHardStatesPng = 'themes/facelift/images/icon_hard_states.png';
const lightIconHardwareSvg = 'themes/facelift/images/icon_hardware.svg';
const lightIconHelpSvg = 'themes/facelift/images/icon_help.svg';
const lightIconHierarchySvg = 'themes/facelift/images/icon_hierarchy.svg';
const lightIconHistoryPng = 'themes/facelift/images/icon_history.png';
const lightIconHomeSvg = 'themes/facelift/images/icon_home.svg';
const lightIconHostPng = 'themes/facelift/images/icon_host.png';
const lightIconHostGraphSvg = 'themes/facelift/images/icon_host_graph.svg';
const lightIconHostProblemsSvg = 'themes/facelift/images/icon_host_problems.svg';
const lightIconHostStateSvg = 'themes/facelift/images/icon_host_state.svg';
const lightIconHostStateSummarySvg = 'themes/facelift/images/icon_host_state_summary.svg';
const lightIconHostStatisticsSvg = 'themes/facelift/images/icon_host_statistics.svg';
const lightIconHostSvcProblemsSvg = 'themes/facelift/images/icon_host_svc_problems.svg';
const lightIconHostSvcProblemsDarkSvg = 'themes/facelift/images/icon_host_svc_problems_dark.svg';
const lightIconHostgroupsSvg = 'themes/facelift/images/icon_hostgroups.svg';
const lightIconHyphenSvg = 'themes/facelift/images/icon_hyphen.svg';
const lightIconIcalPng = 'themes/facelift/images/icon_ical.png';
const lightIconIconsSvg = 'themes/facelift/images/icon_icons.svg';
const lightIconIgnorePng = 'themes/facelift/images/icon_ignore.png';
const lightIconInactivePng = 'themes/facelift/images/icon_inactive.png';
const lightIconInfluxdbConnectionsSvg = 'themes/facelift/images/icon_influxdb_connections.svg';
const lightIconInfoSvg = 'themes/facelift/images/icon_info.svg';
const lightIconInfoCircleSvg = 'themes/facelift/images/icon_info_circle.svg';
const lightIconInlineErrorSvg = 'themes/facelift/images/icon_inline_error.svg';
const lightIconInsertSvg = 'themes/facelift/images/icon_insert.svg';
const lightIconInsertdateSvg = 'themes/facelift/images/icon_insertdate.svg';
const lightIconInstallPng = 'themes/facelift/images/icon_install.png';
const lightIconIntegrationsCustomSvg = 'themes/facelift/images/icon_integrations_custom.svg';
const lightIconIntegrationsOtherSvg = 'themes/facelift/images/icon_integrations_other.svg';
const lightIconInvPng = 'themes/facelift/images/icon_inv.png';
const lightIconInventorySvg = 'themes/facelift/images/icon_inventory.svg';
const lightIconInventoryFailedPng = 'themes/facelift/images/icon_inventory_failed.png';
const lightIconInvertedPng = 'themes/facelift/images/icon_inverted.png';
const lightIconKubernetesSvg = 'themes/facelift/images/icon_kubernetes.svg';
const lightIconLaptop50Png = 'themes/facelift/images/icon_laptop_50.png';
const lightIconLdapSvg = 'themes/facelift/images/icon_ldap.svg';
const lightIconLearningBeginnerSvg = 'themes/facelift/images/icon_learning_beginner.svg';
const lightIconLearningCheckmkSvg = 'themes/facelift/images/icon_learning_checkmk.svg';
const lightIconLearningForumSvg = 'themes/facelift/images/icon_learning_forum.svg';
const lightIconLearningGuideSvg = 'themes/facelift/images/icon_learning_guide.svg';
const lightIconLearningVideoTutorialsSvg =
    'themes/facelift/images/icon_learning_video_tutorials.svg';
const lightIconLicenseFailedPng = 'themes/facelift/images/icon_license_failed.png';
const lightIconLicenseSuccessfulPng = 'themes/facelift/images/icon_license_successful.png';
const lightIconLicenseUnknownStatePng = 'themes/facelift/images/icon_license_unknown_state.png';
const lightIconLicensingSvg = 'themes/facelift/images/icon_licensing.svg';
const lightIconLightbulbSvg = 'themes/facelift/images/icon_lightbulb.svg';
const lightIconLightbulbIdeaSvg = 'themes/facelift/images/icon_lightbulb_idea.svg';
const lightIconLinkPng = 'themes/facelift/images/icon_link.png';
const lightIconLinuxSvg = 'themes/facelift/images/icon_linux.svg';
const lightIconLinuxDebSvg = 'themes/facelift/images/icon_linux_deb.svg';
const lightIconLinuxRpmSvg = 'themes/facelift/images/icon_linux_rpm.svg';
const lightIconLinuxTgzSvg = 'themes/facelift/images/icon_linux_tgz.svg';
const lightIconLocalrulePng = 'themes/facelift/images/icon_localrule.png';
const lightIconLogSvg = 'themes/facelift/images/icon_log.svg';
const lightIconLoginPng = 'themes/facelift/images/icon_login.png';
const lightIconLogwatchPng = 'themes/facelift/images/icon_logwatch.png';
const lightIconMagicMovePng = 'themes/facelift/images/icon_magic_move.png';
const lightIconMainChangesSvg = 'themes/facelift/images/icon_main_changes.svg';
const lightIconMainChangesActiveSvg = 'themes/facelift/images/icon_main_changes_active.svg';
const lightIconMainCustomizeSvg = 'themes/facelift/images/icon_main_customize.svg';
const lightIconMainCustomizeActiveSvg = 'themes/facelift/images/icon_main_customize_active.svg';
const lightIconMainHelpSvg = 'themes/facelift/images/icon_main_help.svg';
const lightIconMainHelpActiveSvg = 'themes/facelift/images/icon_main_help_active.svg';
const lightIconMainMonitoringSvg = 'themes/facelift/images/icon_main_monitoring.svg';
const lightIconMainMonitoringActiveSvg = 'themes/facelift/images/icon_main_monitoring_active.svg';
const lightIconMainSearchSvg = 'themes/facelift/images/icon_main_search.svg';
const lightIconMainSearchActiveSvg = 'themes/facelift/images/icon_main_search_active.svg';
const lightIconMainSetupSvg = 'themes/facelift/images/icon_main_setup.svg';
const lightIconMainSetupActiveSvg = 'themes/facelift/images/icon_main_setup_active.svg';
const lightIconMainUserSvg = 'themes/facelift/images/icon_main_user.svg';
const lightIconMainUserActiveSvg = 'themes/facelift/images/icon_main_user_active.svg';
const lightIconManualSvg = 'themes/facelift/images/icon_manual.svg';
const lightIconManualActiveSvg = 'themes/facelift/images/icon_manual_active.svg';
const lightIconMatrixPng = 'themes/facelift/images/icon_matrix.png';
const lightIconMenuPng = 'themes/facelift/images/icon_menu.png';
const lightIconMenuItemCheckedPng = 'themes/facelift/images/icon_menu_item_checked.png';
const lightIconMenuItemUncheckedPng = 'themes/facelift/images/icon_menu_item_unchecked.png';
const lightIconMessageSvg = 'themes/facelift/images/icon_message.svg';
const lightIconMigrateUsersSvg = 'themes/facelift/images/icon_migrate_users.svg';
const lightIconMissingSvg = 'themes/facelift/images/icon_missing.svg';
const lightIconMkeventdRulesPng = 'themes/facelift/images/icon_mkeventd_rules.png';
const lightIconMkpsSvg = 'themes/facelift/images/icon_mkps.svg';
const lightIconMonitoredServiceSvg = 'themes/facelift/images/icon_monitored_service.svg';
const lightIconMovePng = 'themes/facelift/images/icon_move.png';
const lightIconMovedownPng = 'themes/facelift/images/icon_movedown.png';
const lightIconMoveupPng = 'themes/facelift/images/icon_moveup.png';
const lightIconNagiosSvg = 'themes/facelift/images/icon_nagios.svg';
const lightIconNagvisPng = 'themes/facelift/images/icon_nagvis.png';
const lightIconNeedReplicatePng = 'themes/facelift/images/icon_need_replicate.png';
const lightIconNeedRestartPng = 'themes/facelift/images/icon_need_restart.png';
const lightIconNetworkSvg = 'themes/facelift/images/icon_network.svg';
const lightIconNetworkServicesSvg = 'themes/facelift/images/icon_network_services.svg';
const lightIconNetworkTopologySvg = 'themes/facelift/images/icon_network_topology.svg';
const lightIconNetworkingSvg = 'themes/facelift/images/icon_networking.svg';
const lightIconNewSvg = 'themes/facelift/images/icon_new.svg';
const lightIconNewClusterPng = 'themes/facelift/images/icon_new_cluster.png';
const lightIconNewMkpPng = 'themes/facelift/images/icon_new_mkp.png';
const lightIconNewfolderPng = 'themes/facelift/images/icon_newfolder.png';
const lightIconNoEntrySvg = 'themes/facelift/images/icon_no_entry.svg';
const lightIconNoPendingChangesSvg = 'themes/facelift/images/icon_no_pending_changes.svg';
const lightIconNoRevertSvg = 'themes/facelift/images/icon_no_revert.svg';
const lightIconNodowntimePng = 'themes/facelift/images/icon_nodowntime.png';
const lightIconNotesPng = 'themes/facelift/images/icon_notes.png';
const lightIconNotifDisabledPng = 'themes/facelift/images/icon_notif_disabled.png';
const lightIconNotifEnabledPng = 'themes/facelift/images/icon_notif_enabled.png';
const lightIconNotifManDisabledPng = 'themes/facelift/images/icon_notif_man_disabled.png';
const lightIconNotificationEnabledPng = 'themes/facelift/images/icon_notification_enabled.png';
const lightIconNotificationTimelineSvg = 'themes/facelift/images/icon_notification_timeline.svg';
const lightIconNotificationsSvg = 'themes/facelift/images/icon_notifications.svg';
const lightIconNpassivePng = 'themes/facelift/images/icon_npassive.png';
const lightIconNtopSvg = 'themes/facelift/images/icon_ntop.svg';
const lightIconOpenTelemetrySvg = 'themes/facelift/images/icon_open_telemetry.svg';
const lightIconOpentelemetrySvg = 'themes/facelift/images/icon_opentelemetry.svg';
const lightIconOsOtherSvg = 'themes/facelift/images/icon_os_other.svg';
const lightIconOtelCollectorSvg = 'themes/facelift/images/icon_otel_collector.svg';
const lightIconOutofServiceperiodPng = 'themes/facelift/images/icon_outof_serviceperiod.png';
const lightIconOutofnotPng = 'themes/facelift/images/icon_outofnot.png';
const lightIconPackagesSvg = 'themes/facelift/images/icon_packages.svg';
const lightIconPagetypeTopicSvg = 'themes/facelift/images/icon_pagetype_topic.svg';
const lightIconPageurlSvg = 'themes/facelift/images/icon_pageurl.svg';
const lightIconPainteroptionsSvg = 'themes/facelift/images/icon_painteroptions.svg';
const lightIconPainteroptionsDownHiPng = 'themes/facelift/images/icon_painteroptions_down_hi.png';
const lightIconPainteroptionsDownLoPng = 'themes/facelift/images/icon_painteroptions_down_lo.png';
const lightIconPainteroptionsOffPng = 'themes/facelift/images/icon_painteroptions_off.png';
const lightIconParentscanPng = 'themes/facelift/images/icon_parentscan.png';
const lightIconPasswordsSvg = 'themes/facelift/images/icon_passwords.svg';
const lightIconPausePng = 'themes/facelift/images/icon_pause.png';
const lightIconPendingChangesSvg = 'themes/facelift/images/icon_pending_changes.svg';
const lightIconPendingTaskSvg = 'themes/facelift/images/icon_pending_task.svg';
const lightIconPercentageOfServiceProblemsSvg =
    'themes/facelift/images/icon_percentage-of-service-problems.svg';
const lightIconPerformanceDataSvg = 'themes/facelift/images/icon_performance_data.svg';
const lightIconPersistPng = 'themes/facelift/images/icon_persist.png';
const lightIconPieChartPng = 'themes/facelift/images/icon_pie_chart.png';
const lightIconPluginsAgentlessSvg = 'themes/facelift/images/icon_plugins_agentless.svg';
const lightIconPluginsAppPng = 'themes/facelift/images/icon_plugins_app.png';
const lightIconPluginsCloudSvg = 'themes/facelift/images/icon_plugins_cloud.svg';
const lightIconPluginsContainerizationSvg =
    'themes/facelift/images/icon_plugins_containerization.svg';
const lightIconPluginsGenericSvg = 'themes/facelift/images/icon_plugins_generic.svg';
const lightIconPluginsHwPng = 'themes/facelift/images/icon_plugins_hw.png';
const lightIconPluginsOsSvg = 'themes/facelift/images/icon_plugins_os.svg';
const lightIconPluginsVirtualSvg = 'themes/facelift/images/icon_plugins_virtual.svg';
const lightIconPlusSvg = 'themes/facelift/images/icon_plus.svg';
const lightIconPnpPng = 'themes/facelift/images/icon_pnp.png';
const lightIconPredefinedConditionsSvg = 'themes/facelift/images/icon_predefined_conditions.svg';
const lightIconPredictionPng = 'themes/facelift/images/icon_prediction.png';
const lightIconProblemSvg = 'themes/facelift/images/icon_problem.svg';
const lightIconProductSvg = 'themes/facelift/images/icon_product.svg';
const lightIconPrometheusSvg = 'themes/facelift/images/icon_prometheus.svg';
const lightIconQaSvg = 'themes/facelift/images/icon_qa.svg';
const lightIconQsAwsSvg = 'themes/facelift/images/icon_qs_aws.svg';
const lightIconQsAzureSvg = 'themes/facelift/images/icon_qs_azure.svg';
const lightIconQsGcpSvg = 'themes/facelift/images/icon_qs_gcp.svg';
const lightIconQsOtelSvg = 'themes/facelift/images/icon_qs_otel.svg';
const lightIconQsPrometheusSvg = 'themes/facelift/images/icon_qs_prometheus.svg';
const lightIconQsRelaySvg = 'themes/facelift/images/icon_qs_relay.svg';
const lightIconQuickSetupAwsSvg = 'themes/facelift/images/icon_quick_setup_aws.svg';
const lightIconQuicksearchPng = 'themes/facelift/images/icon_quicksearch.png';
const lightIconRandomPng = 'themes/facelift/images/icon_random.png';
const lightIconRankSvg = 'themes/facelift/images/icon_rank.svg';
const lightIconReadOnlySvg = 'themes/facelift/images/icon_read_only.svg';
const lightIconRecreateBrokerCertificateSvg =
    'themes/facelift/images/icon_recreate_broker_certificate.svg';
const lightIconRedoSvg = 'themes/facelift/images/icon_redo.svg';
const lightIconRelayMenuSvg = 'themes/facelift/images/icon_relay_menu.svg';
const lightIconReleaseMkpPng = 'themes/facelift/images/icon_release_mkp.png';
const lightIconReleaseMkpYellowPng = 'themes/facelift/images/icon_release_mkp_yellow.png';
const lightIconReloadSvg = 'themes/facelift/images/icon_reload.svg';
const lightIconReloadCmkSvg = 'themes/facelift/images/icon_reload_cmk.svg';
const lightIconReloadsnapinPng = 'themes/facelift/images/icon_reloadsnapin.png';
const lightIconReloadsnapinLoAltPng = 'themes/facelift/images/icon_reloadsnapin_lo_alt.png';
const lightIconRenameHostSvg = 'themes/facelift/images/icon_rename_host.svg';
const lightIconRepl25Png = 'themes/facelift/images/icon_repl_25.png';
const lightIconRepl50Png = 'themes/facelift/images/icon_repl_50.png';
const lightIconRepl75Png = 'themes/facelift/images/icon_repl_75.png';
const lightIconReplFailedPng = 'themes/facelift/images/icon_repl_failed.png';
const lightIconReplLockedPng = 'themes/facelift/images/icon_repl_locked.png';
const lightIconReplPendingPng = 'themes/facelift/images/icon_repl_pending.png';
const lightIconReplSuccessPng = 'themes/facelift/images/icon_repl_success.png';
const lightIconReplayPng = 'themes/facelift/images/icon_replay.png';
const lightIconReplicatePng = 'themes/facelift/images/icon_replicate.png';
const lightIconReportSvg = 'themes/facelift/images/icon_report.svg';
const lightIconReportElementPng = 'themes/facelift/images/icon_report_element.png';
const lightIconReportFixedPng = 'themes/facelift/images/icon_report_fixed.png';
const lightIconReportStorePng = 'themes/facelift/images/icon_report_store.png';
const lightIconReportschedulerPng = 'themes/facelift/images/icon_reportscheduler.png';
const lightIconResetPng = 'themes/facelift/images/icon_reset.png';
const lightIconResetcountersPng = 'themes/facelift/images/icon_resetcounters.png';
const lightIconResizePng = 'themes/facelift/images/icon_resize.png';
const lightIconRestartPng = 'themes/facelift/images/icon_restart.png';
const lightIconRestorePng = 'themes/facelift/images/icon_restore.png';
const lightIconRevertSvg = 'themes/facelift/images/icon_revert.svg';
const lightIconRj4550Png = 'themes/facelift/images/icon_rj45_50.png';
const lightIconRolesSvg = 'themes/facelift/images/icon_roles.svg';
const lightIconRotateLeftPng = 'themes/facelift/images/icon_rotate_left.png';
const lightIconRuleSvg = 'themes/facelift/images/icon_rule.svg';
const lightIconRuleNoPng = 'themes/facelift/images/icon_rule_no.png';
const lightIconRuleNoOffPng = 'themes/facelift/images/icon_rule_no_off.png';
const lightIconRuleYesPng = 'themes/facelift/images/icon_rule_yes.png';
const lightIconRuleYesOffPng = 'themes/facelift/images/icon_rule_yes_off.png';
const lightIconRulesSvg = 'themes/facelift/images/icon_rules.svg';
const lightIconRulesetsSvg = 'themes/facelift/images/icon_rulesets.svg';
const lightIconRulesetsDeprecatedPng = 'themes/facelift/images/icon_rulesets_deprecated.png';
const lightIconRulesetsIneffectivePng = 'themes/facelift/images/icon_rulesets_ineffective.png';
const lightIconSaasSvg = 'themes/facelift/images/icon_saas.svg';
const lightIconSamlSvg = 'themes/facelift/images/icon_saml.svg';
const lightIconSaveSvg = 'themes/facelift/images/icon_save.svg';
const lightIconSaveDashboardSvg = 'themes/facelift/images/icon_save_dashboard.svg';
const lightIconSaveGraphSvg = 'themes/facelift/images/icon_save_graph.svg';
const lightIconSaveToFolderSvg = 'themes/facelift/images/icon_save_to_folder.svg';
const lightIconSaveToServicesSvg = 'themes/facelift/images/icon_save_to_services.svg';
const lightIconSaveViewSvg = 'themes/facelift/images/icon_save_view.svg';
const lightIconScatterplotSvg = 'themes/facelift/images/icon_scatterplot.svg';
const lightIconSearchSvg = 'themes/facelift/images/icon_search.svg';
const lightIconSearchActionSvg = 'themes/facelift/images/icon_search_action.svg';
const lightIconSearchActionButtonSvg = 'themes/facelift/images/icon_search_action_button.svg';
const lightIconSelectArrowSvg = 'themes/facelift/images/icon_select_arrow.svg';
const lightIconServiceDiscoverySvg = 'themes/facelift/images/icon_service_discovery.svg';
const lightIconServiceDurationSvg = 'themes/facelift/images/icon_service_duration.svg';
const lightIconServiceGraphSvg = 'themes/facelift/images/icon_service_graph.svg';
const lightIconServiceLabelAddSvg = 'themes/facelift/images/icon_service_label_add.svg';
const lightIconServiceLabelRemoveSvg = 'themes/facelift/images/icon_service_label_remove.svg';
const lightIconServiceLabelUpdateSvg = 'themes/facelift/images/icon_service_label_update.svg';
const lightIconServiceStateSvg = 'themes/facelift/images/icon_service_state.svg';
const lightIconServiceToDisabledSvg = 'themes/facelift/images/icon_service_to_disabled.svg';
const lightIconServiceToIgnoredSvg = 'themes/facelift/images/icon_service_to_ignored.svg';
const lightIconServiceToMonitoredSvg = 'themes/facelift/images/icon_service_to_monitored.svg';
const lightIconServiceToNewSvg = 'themes/facelift/images/icon_service_to_new.svg';
const lightIconServiceToRemovedSvg = 'themes/facelift/images/icon_service_to_removed.svg';
const lightIconServiceToUnchangedSvg = 'themes/facelift/images/icon_service_to_unchanged.svg';
const lightIconServiceToUndecidedSvg = 'themes/facelift/images/icon_service_to_undecided.svg';
const lightIconServicegroupsSvg = 'themes/facelift/images/icon_servicegroups.svg';
const lightIconServicesSvg = 'themes/facelift/images/icon_services.svg';
const lightIconServicesBlueSvg = 'themes/facelift/images/icon_services_blue.svg';
const lightIconServicesFixAllSvg = 'themes/facelift/images/icon_services_fix_all.svg';
const lightIconServicesGreenSvg = 'themes/facelift/images/icon_services_green.svg';
const lightIconServicesRefreshSvg = 'themes/facelift/images/icon_services_refresh.svg';
const lightIconServicesStopPng = 'themes/facelift/images/icon_services_stop.png';
const lightIconServicesTabulaRasaSvg = 'themes/facelift/images/icon_services_tabula_rasa.svg';
const lightIconShowLessSvg = 'themes/facelift/images/icon_show_less.svg';
const lightIconShowLessGreenSvg = 'themes/facelift/images/icon_show_less_green.svg';
const lightIconShowMoreSvg = 'themes/facelift/images/icon_show_more.svg';
const lightIconShowMoreGreenSvg = 'themes/facelift/images/icon_show_more_green.svg';
const lightIconShowbiPng = 'themes/facelift/images/icon_showbi.png';
const lightIconShowhidePng = 'themes/facelift/images/icon_showhide.png';
const lightIconSidebarSvg = 'themes/facelift/images/icon_sidebar.svg';
const lightIconSidebarFoldedSvg = 'themes/facelift/images/icon_sidebar_folded.svg';
const lightIconSidebarLogoutSvg = 'themes/facelift/images/icon_sidebar_logout.svg';
const lightIconSidebarPositionSvg = 'themes/facelift/images/icon_sidebar_position.svg';
const lightIconSignSvg = 'themes/facelift/images/icon_sign.svg';
const lightIconSignatureKeySvg = 'themes/facelift/images/icon_signature_key.svg';
const lightIconSignatureKeyPartialPng = 'themes/facelift/images/icon_signature_key_partial.png';
const lightIconSingleMetricSvg = 'themes/facelift/images/icon_single_metric.svg';
const lightIconSiteDeadSvg = 'themes/facelift/images/icon_site_dead.svg';
const lightIconSiteDisabledSvg = 'themes/facelift/images/icon_site_disabled.svg';
const lightIconSiteDownSvg = 'themes/facelift/images/icon_site_down.svg';
const lightIconSiteGlobalsPng = 'themes/facelift/images/icon_site_globals.png';
const lightIconSiteGlobalsModifiedPng = 'themes/facelift/images/icon_site_globals_modified.png';
const lightIconSiteMissingSvg = 'themes/facelift/images/icon_site_missing.svg';
const lightIconSiteOverviewSvg = 'themes/facelift/images/icon_site_overview.svg';
const lightIconSiteUnreachSvg = 'themes/facelift/images/icon_site_unreach.svg';
const lightIconSiteWaitingSvg = 'themes/facelift/images/icon_site_waiting.svg';
const lightIconSitesSvg = 'themes/facelift/images/icon_sites.svg';
const lightIconSlaSvg = 'themes/facelift/images/icon_sla.svg';
const lightIconSlaConfigurationPng = 'themes/facelift/images/icon_sla_configuration.png';
const lightIconSnapinGreyswitchOffPng = 'themes/facelift/images/icon_snapin_greyswitch_off.png';
const lightIconSnapinGreyswitchOnPng = 'themes/facelift/images/icon_snapin_greyswitch_on.png';
const lightIconSnapshotPng = 'themes/facelift/images/icon_snapshot.png';
const lightIconSnapshotChecksumPng = 'themes/facelift/images/icon_snapshot_checksum.png';
const lightIconSnapshotNchecksumPng = 'themes/facelift/images/icon_snapshot_nchecksum.png';
const lightIconSnapshotPchecksumPng = 'themes/facelift/images/icon_snapshot_pchecksum.png';
const lightIconSnmpSvg = 'themes/facelift/images/icon_snmp.svg';
const lightIconSnmpmibSvg = 'themes/facelift/images/icon_snmpmib.svg';
const lightIconSoftwareSvg = 'themes/facelift/images/icon_software.svg';
const lightIconSolarisPkgSvg = 'themes/facelift/images/icon_solaris_pkg.svg';
const lightIconSolarisTgzSvg = 'themes/facelift/images/icon_solaris_tgz.svg';
const lightIconSparkleSvg = 'themes/facelift/images/icon_sparkle.svg';
const lightIconSparkleWhiteSvg = 'themes/facelift/images/icon_sparkle_white.svg';
const lightIconStaleSvg = 'themes/facelift/images/icon_stale.svg';
const lightIconStarredPng = 'themes/facelift/images/icon_starred.png';
const lightIconStartPng = 'themes/facelift/images/icon_start.png';
const lightIconStaticChecksSvg = 'themes/facelift/images/icon_static_checks.svg';
const lightIconStaticTextSvg = 'themes/facelift/images/icon_static_text.svg';
const lightIconStatusSvg = 'themes/facelift/images/icon_status.svg';
const lightIconSuggestionSvg = 'themes/facelift/images/icon_suggestion.svg';
const lightIconSvcProblemsSvg = 'themes/facelift/images/icon_svc_problems.svg';
const lightIconSyncGraphsPng = 'themes/facelift/images/icon_sync_graphs.png';
const lightIconSyncMkpPng = 'themes/facelift/images/icon_sync_mkp.png';
const lightIconSyntheticMonitoringPurpleSvg =
    'themes/facelift/images/icon_synthetic_monitoring_purple.svg';
const lightIconSyntheticMonitoringTopicSvg =
    'themes/facelift/images/icon_synthetic_monitoring_topic.svg';
const lightIconSyntheticMonitoringYellowSvg =
    'themes/facelift/images/icon_synthetic_monitoring_yellow.svg';
const lightIconTableActionsOffSvg = 'themes/facelift/images/icon_table_actions_off.svg';
const lightIconTableActionsOnSvg = 'themes/facelift/images/icon_table_actions_on.svg';
const lightIconTagSvg = 'themes/facelift/images/icon_tag.svg';
const lightIconTickSvg = 'themes/facelift/images/icon_tick.svg';
const lightIconTimelinePng = 'themes/facelift/images/icon_timeline.png';
const lightIconTimeperiodsSvg = 'themes/facelift/images/icon_timeperiods.svg';
const lightIconTimewarpPng = 'themes/facelift/images/icon_timewarp.png';
const lightIconTimewarpOffPng = 'themes/facelift/images/icon_timewarp_off.png';
const lightIconTlsSvg = 'themes/facelift/images/icon_tls.svg';
const lightIconToggleContextPng = 'themes/facelift/images/icon_toggle_context.png';
const lightIconToggleDetailsPng = 'themes/facelift/images/icon_toggle_details.png';
const lightIconToggleOffSvg = 'themes/facelift/images/icon_toggle_off.svg';
const lightIconToggleOnSvg = 'themes/facelift/images/icon_toggle_on.svg';
const lightIconTopPng = 'themes/facelift/images/icon_top.png';
const lightIconTopListSvg = 'themes/facelift/images/icon_top-list.svg';
const lightIconTopic2faSvg = 'themes/facelift/images/icon_topic_2fa.svg';
const lightIconTopicAdministrationPng = 'themes/facelift/images/icon_topic_administration.png';
const lightIconTopicAgentsPng = 'themes/facelift/images/icon_topic_agents.png';
const lightIconTopicAnalyzePng = 'themes/facelift/images/icon_topic_analyze.png';
const lightIconTopicApplicationsPng = 'themes/facelift/images/icon_topic_applications.png';
const lightIconTopicBiPng = 'themes/facelift/images/icon_topic_bi.png';
const lightIconTopicChangePasswordPng = 'themes/facelift/images/icon_topic_change_password.png';
const lightIconTopicCheckmkSvg = 'themes/facelift/images/icon_topic_checkmk.svg';
const lightIconTopicEventsPng = 'themes/facelift/images/icon_topic_events.png';
const lightIconTopicExporterSvg = 'themes/facelift/images/icon_topic_exporter.svg';
const lightIconTopicGeneralPng = 'themes/facelift/images/icon_topic_general.png';
const lightIconTopicGraphsPng = 'themes/facelift/images/icon_topic_graphs.png';
const lightIconTopicHistoryPng = 'themes/facelift/images/icon_topic_history.png';
const lightIconTopicHostsPng = 'themes/facelift/images/icon_topic_hosts.png';
const lightIconTopicInventoryPng = 'themes/facelift/images/icon_topic_inventory.png';
const lightIconTopicMaintenancePng = 'themes/facelift/images/icon_topic_maintenance.png';
const lightIconTopicMonitoringSvg = 'themes/facelift/images/icon_topic_monitoring.svg';
const lightIconTopicMyWorkplaceSvg = 'themes/facelift/images/icon_topic_my_workplace.svg';
const lightIconTopicNetworkSvg = 'themes/facelift/images/icon_topic_network.svg';
const lightIconTopicOtherPng = 'themes/facelift/images/icon_topic_other.png';
const lightIconTopicOverviewPng = 'themes/facelift/images/icon_topic_overview.png';
const lightIconTopicProblemsPng = 'themes/facelift/images/icon_topic_problems.png';
const lightIconTopicProfilePng = 'themes/facelift/images/icon_topic_profile.png';
const lightIconTopicQuickSetupsSvg = 'themes/facelift/images/icon_topic_quick_setups.svg';
const lightIconTopicReportingSvg = 'themes/facelift/images/icon_topic_reporting.svg';
const lightIconTopicServicesPng = 'themes/facelift/images/icon_topic_services.png';
const lightIconTopicSitePng = 'themes/facelift/images/icon_topic_site.png';
const lightIconTopicSystemSvg = 'themes/facelift/images/icon_topic_system.svg';
const lightIconTopicUserInterfaceSvg = 'themes/facelift/images/icon_topic_user_interface.svg';
const lightIconTopicUsersPng = 'themes/facelift/images/icon_topic_users.png';
const lightIconTopicVisualizationPng = 'themes/facelift/images/icon_topic_visualization.png';
const lightIconTransSvg = 'themes/facelift/images/icon_trans.svg';
const lightIconTreeClosedSvg = 'themes/facelift/images/icon_tree_closed.svg';
const lightIconTrustPng = 'themes/facelift/images/icon_trust.png';
const lightIconUnacknowledgeTestPng = 'themes/facelift/images/icon_unacknowledge_test.png';
const lightIconUnavailableSvg = 'themes/facelift/images/icon_unavailable.svg';
const lightIconUndecidedServiceSvg = 'themes/facelift/images/icon_undecided_service.svg';
const lightIconUndoSvg = 'themes/facelift/images/icon_undo.svg';
const lightIconUnpackagedFilesPng = 'themes/facelift/images/icon_unpackaged_files.png';
const lightIconUnusedbirulesPng = 'themes/facelift/images/icon_unusedbirules.png';
const lightIconUpPng = 'themes/facelift/images/icon_up.png';
const lightIconUpdatePng = 'themes/facelift/images/icon_update.png';
const lightIconUpdateDiscoveryParametersSvg =
    'themes/facelift/images/icon_update_discovery_parameters.svg';
const lightIconUpdateHostLabelsSvg = 'themes/facelift/images/icon_update_host_labels.svg';
const lightIconUpdateServiceLabelsSvg = 'themes/facelift/images/icon_update_service_labels.svg';
const lightIconUpgradeSvg = 'themes/facelift/images/icon_upgrade.svg';
const lightIconUploadPng = 'themes/facelift/images/icon_upload.png';
const lightIconUrlPng = 'themes/facelift/images/icon_url.png';
const lightIconUsedrulesetsPng = 'themes/facelift/images/icon_usedrulesets.png';
const lightIconUserLockedPng = 'themes/facelift/images/icon_user_locked.png';
const lightIconUsersSvg = 'themes/facelift/images/icon_users.svg';
const lightIconUXSvg = 'themes/facelift/images/icon_ux.svg';
const lightIconValidationErrorPng = 'themes/facelift/images/icon_validation_error.png';
const lightIconVideoPng = 'themes/facelift/images/icon_video.png';
const lightIconViewSvg = 'themes/facelift/images/icon_view.svg';
const lightIconViewColumnsPng = 'themes/facelift/images/icon_view_columns.png';
const lightIconViewCopySvg = 'themes/facelift/images/icon_view_copy.svg';
const lightIconViewLinkSvg = 'themes/facelift/images/icon_view_link.svg';
const lightIconViewRefreshPng = 'themes/facelift/images/icon_view_refresh.png';
const lightIconVsphereSvg = 'themes/facelift/images/icon_vsphere.svg';
const lightIconWarningPng = 'themes/facelift/images/icon_warning.png';
const lightIconWatoPng = 'themes/facelift/images/icon_wato.png';
const lightIconWatoChangesPng = 'themes/facelift/images/icon_wato_changes.png';
const lightIconWatoNochangesPng = 'themes/facelift/images/icon_wato_nochanges.png';
const lightIconWerkAckPng = 'themes/facelift/images/icon_werk_ack.png';
const lightIconWidgetCloneSvg = 'themes/facelift/images/icon_widget_clone.svg';
const lightIconWidgetDeleteSvg = 'themes/facelift/images/icon_widget_delete.svg';
const lightIconWidgetEditSvg = 'themes/facelift/images/icon_widget_edit.svg';
const lightIconWikisearchPng = 'themes/facelift/images/icon_wikisearch.png';
const lightIconWindowsMsiSvg = 'themes/facelift/images/icon_windows_msi.svg';
const lightIconWrongAgentPng = 'themes/facelift/images/icon_wrong_agent.png';
const lightIconWwwPng = 'themes/facelift/images/icon_www.png';
const lightIconZoomPng = 'themes/facelift/images/icon_zoom.png';
const lightLoadGraphPng = 'themes/facelift/images/load_graph.png';
const lightLogoCmkSmallPng = 'themes/facelift/images/logo_cmk_small.png';
const lightOoservicePng = 'themes/facelift/images/ooservice.png';
const lightPluginurlPng = 'themes/facelift/images/pluginurl.png';
const lightQuicksearchFieldBgPng = 'themes/facelift/images/quicksearch_field_bg.png';
const lightReleaseAutomatedSvg = 'themes/facelift/images/release_automated.svg';
const lightReleaseDeploySvg = 'themes/facelift/images/release_deploy.svg';
const lightReleaseScaleSvg = 'themes/facelift/images/release_scale.svg';
const lightResizeGraphPng = 'themes/facelift/images/resize_graph.png';
const lightSidebarTopPng = 'themes/facelift/images/sidebar_top.png';
const lightSomeproblemPng = 'themes/facelift/images/someproblem.png';
const lightSpeedometerSvg = 'themes/facelift/images/speedometer.svg';
const lightStatusReportPng = 'themes/facelift/images/status_report.png';
const darkDashletCloneSvg = 'themes/modern-dark/images/dashlet_clone.svg';
const darkDashletDeleteSvg = 'themes/modern-dark/images/dashlet_delete.svg';
const darkDashletEditSvg = 'themes/modern-dark/images/dashlet_edit.svg';
const darkIconAddRuleSvg = 'themes/modern-dark/images/icon_add_rule.svg';
const darkIconAgentRegistrationSvg = 'themes/modern-dark/images/icon_agent_registration.svg';
const darkIconAnalyzeSvg = 'themes/modern-dark/images/icon_analyze.svg';
const darkIconAssignSvg = 'themes/modern-dark/images/icon_assign.svg';
const darkIconAwsSvg = 'themes/modern-dark/images/icon_aws.svg';
const darkIconCancelNotificationsSvg = 'themes/modern-dark/images/icon_cancel_notifications.svg';
const darkIconCheckmarkBgWhiteSvg = 'themes/modern-dark/images/icon_checkmark_bg_white.svg';
const darkIconCheckmarkOrangeSvg = 'themes/modern-dark/images/icon_checkmark_orange.svg';
const darkIconCheckmarkPlusSvg = 'themes/modern-dark/images/icon_checkmark_plus.svg';
const darkIconCloseSvg = 'themes/modern-dark/images/icon_close.svg';
const darkIconCommentSvg = 'themes/modern-dark/images/icon_comment.svg';
const darkIconConfigurationSvg = 'themes/modern-dark/images/icon_configuration.svg';
const darkIconCrossBgWhiteSvg = 'themes/modern-dark/images/icon_cross_bg_white.svg';
const darkIconDashboardGridSvg = 'themes/modern-dark/images/icon_dashboard_grid.svg';
const darkIconDashboardMenuarrowSvg = 'themes/modern-dark/images/icon_dashboard_menuarrow.svg';
const darkIconDevelopmentSvg = 'themes/modern-dark/images/icon_development.svg';
const darkIconDragSvg = 'themes/modern-dark/images/icon_drag.svg';
const darkIconExportLinkSvg = 'themes/modern-dark/images/icon_export_link.svg';
const darkIconExternalSvg = 'themes/modern-dark/images/icon_external.svg';
const darkIconFavoriteSvg = 'themes/modern-dark/images/icon_favorite.svg';
const darkIconFilterLineSvg = 'themes/modern-dark/images/icon_filter_line.svg';
const darkIconFixallSvg = 'themes/modern-dark/images/icon_fixall.svg';
const darkIconFolderBlueSvg = 'themes/modern-dark/images/icon_folder_blue.svg';
const darkIconHelpSvg = 'themes/modern-dark/images/icon_help.svg';
const darkIconHomeSvg = 'themes/modern-dark/images/icon_home.svg';
const darkIconHostSvcProblemsSvg = 'themes/modern-dark/images/icon_host_svc_problems.svg';
const darkIconHyphenSvg = 'themes/modern-dark/images/icon_hyphen.svg';
const darkIconInfoCircleSvg = 'themes/modern-dark/images/icon_info_circle.svg';
const darkIconMainChangesSvg = 'themes/modern-dark/images/icon_main_changes.svg';
const darkIconMainCustomizeSvg = 'themes/modern-dark/images/icon_main_customize.svg';
const darkIconMainHelpSvg = 'themes/modern-dark/images/icon_main_help.svg';
const darkIconMainMonitoringSvg = 'themes/modern-dark/images/icon_main_monitoring.svg';
const darkIconMainSearchSvg = 'themes/modern-dark/images/icon_main_search.svg';
const darkIconMainSetupSvg = 'themes/modern-dark/images/icon_main_setup.svg';
const darkIconMainUserSvg = 'themes/modern-dark/images/icon_main_user.svg';
const darkIconManualSvg = 'themes/modern-dark/images/icon_manual.svg';
const darkIconNagiosSvg = 'themes/modern-dark/images/icon_nagios.svg';
const darkIconNetworkSvg = 'themes/modern-dark/images/icon_network.svg';
const darkIconPerformanceDataSvg = 'themes/modern-dark/images/icon_performance_data.svg';
const darkIconProductSvg = 'themes/modern-dark/images/icon_product.svg';
const darkIconQaSvg = 'themes/modern-dark/images/icon_qa.svg';
const darkIconReloadCmkSvg = 'themes/modern-dark/images/icon_reload_cmk.svg';
const darkIconRulesetsSvg = 'themes/modern-dark/images/icon_rulesets.svg';
const darkIconSaasSvg = 'themes/modern-dark/images/icon_saas.svg';
const darkIconSearchSvg = 'themes/modern-dark/images/icon_search.svg';
const darkIconSearchActionSvg = 'themes/modern-dark/images/icon_search_action.svg';
const darkIconSearchActionButtonSvg = 'themes/modern-dark/images/icon_search_action_button.svg';
const darkIconSelectArrowSvg = 'themes/modern-dark/images/icon_select_arrow.svg';
const darkIconServicesBlueSvg = 'themes/modern-dark/images/icon_services_blue.svg';
const darkIconShowLessSvg = 'themes/modern-dark/images/icon_show_less.svg';
const darkIconShowMoreSvg = 'themes/modern-dark/images/icon_show_more.svg';
const darkIconSidebarFoldedSvg = 'themes/modern-dark/images/icon_sidebar_folded.svg';
const darkIconSiteDeadSvg = 'themes/modern-dark/images/icon_site_dead.svg';
const darkIconSiteDisabledSvg = 'themes/modern-dark/images/icon_site_disabled.svg';
const darkIconSiteDownSvg = 'themes/modern-dark/images/icon_site_down.svg';
const darkIconSiteMissingSvg = 'themes/modern-dark/images/icon_site_missing.svg';
const darkIconSiteUnreachSvg = 'themes/modern-dark/images/icon_site_unreach.svg';
const darkIconSiteWaitingSvg = 'themes/modern-dark/images/icon_site_waiting.svg';
const darkIconSnmpmibSvg = 'themes/modern-dark/images/icon_snmpmib.svg';
const darkIconSparkleSvg = 'themes/modern-dark/images/icon_sparkle.svg';
const darkIconSparkleWhiteSvg = 'themes/modern-dark/images/icon_sparkle_white.svg';
const darkIconStaleSvg = 'themes/modern-dark/images/icon_stale.svg';
const darkIconSuggestionSvg = 'themes/modern-dark/images/icon_suggestion.svg';
const darkIconTableActionsOffSvg = 'themes/modern-dark/images/icon_table_actions_off.svg';
const darkIconTableActionsOnSvg = 'themes/modern-dark/images/icon_table_actions_on.svg';
const darkIconTickSvg = 'themes/modern-dark/images/icon_tick.svg';
const darkIconToggleOffSvg = 'themes/modern-dark/images/icon_toggle_off.svg';
const darkIconTreeClosedSvg = 'themes/modern-dark/images/icon_tree_closed.svg';
const darkIconUnavailableSvg = 'themes/modern-dark/images/icon_unavailable.svg';
const darkIconUXSvg = 'themes/modern-dark/images/icon_ux.svg';
const darkReleaseAutomatedSvg = 'themes/modern-dark/images/release_automated.svg';
const darkSpeedometerSvg = 'themes/modern-dark/images/speedometer.svg';

export const emblems = [
    'add',
    'api',
    'disable',
    'download',
    'downtime',
    'edit',
    'enable',
    'more',
    'pending',
    'refresh',
    'remove',
    'rulesets',
    'search',
    'settings',
    'sign',
    'statistic',
    'time',
    'trans',
    'warning',
] as const;

export const oneColorIcons = [
    'changes',
    'check-circle',
    'checkmark',
    'customize',
    'db-widget-clone',
    'db-widget-delete',
    'db-widget-edit',
    'error',
    'help',
    'info',
    'menu',
    'monitoring',
    'saas',
    'search',
    'services',
    'setup',
    'show-less',
    'show-more',
    'sidebar',
    'success',
    'user',
    'warning',
    'back',
    'chain',
    'broken-chain',
    'share',
] as const;
export const twoColorIcons = ['aggr'] as const;

export const iconSizes: Record<IconSizes, number> = {
    xxsmall: 8,
    xsmall: 10,
    small: 12,
    medium: 15,
    large: 18,
    xlarge: 20,
    xxlarge: 32,
    xxxlarge: 77,
};

export const cmkIconVariants = cva('', {
    variants: {
        variant: {
            plain: '',
            inline: 'cmk-icon--inline',
        },
        colored: {
            true: '',
            false: 'cmk-icon--colorless',
        },
        size: {
            xxsmall: 'cmk-icon--xxsmall',
            xsmall: 'cmk-icon--xsmall',
            small: 'cmk-icon--small',
            medium: 'cmk-icon--medium',
            large: 'cmk-icon--large',
            xlarge: 'cmk-icon--xlarge',
            xxlarge: 'cmk-icon--xxlarge',
            xxxlarge: 'cmk-icon--xxxlarge',
        } satisfies Record<IconSizes, string>,
    },
    defaultVariants: {
        variant: 'plain',
        colored: true,
        size: 'medium',
    },
});

export const cmkMultitoneIconVariants = cva('', {
    variants: {
        color: {
            success: 'green',
            hosts: 'blue',
            info: 'blue',
            warning: 'yellow',
            services: 'yellow',
            danger: 'red',
            customization: 'pink',
            others: 'grey',
            users: 'purple',
            specialAgents: 'cyan',
            font: 'font',
        },
    },
});

export const unthemedIcons: Partial<Record<IconNames | '2fa' | '2fa-backup-codes', string>> = {
    '2fa': lightIcon2faSvg,
    '2fa-backup-codes': lightIcon2faBackupCodesSvg,
    abort: lightIconAbortPng,
    'about-checkmk': lightIconAboutCheckmkSvg,
    accept: lightIconAcceptSvg,
    'accept-all': lightIconAcceptAllSvg,
    ack: lightIconAckPng,
    'acknowledge-test': lightIconAcknowledgeTestPng,
    action: lightIconActionPng,
    activate: lightIconActivatePng,
    add: lightIconAddPng,
    'add-dashlet': lightIconAddDashletPng,
    'agent-output': lightIconAgentOutputPng,
    agents: lightIconAgentsSvg,
    aggr: lightIconAggrSvg,
    'aggr-single': lightIconAggrSingleSvg,
    'aggr-single-problem': lightIconAggrSingleProblemSvg,
    aggrcomp: lightIconAggrcompPng,
    'aix-tgz': lightIconAixTgzSvg,
    alert: lightIconAlertPng,
    'alert-ack': lightIconAlertAckPng,
    'alert-ackstop': lightIconAlertAckstopPng,
    'alert-alert-handler-failed': lightIconAlertAlertHandlerFailedPng,
    'alert-alert-handler-started': lightIconAlertAlertHandlerStartedPng,
    'alert-alert-handler-stopped': lightIconAlertAlertHandlerStoppedPng,
    'alert-cmk-notify': lightIconAlertCmkNotifyPng,
    'alert-command': lightIconAlertCommandPng,
    'alert-crit': lightIconAlertCritSvg,
    'alert-down': lightIconAlertDownPng,
    'alert-downtime': lightIconAlertDowntimePng,
    'alert-downtimestop': lightIconAlertDowntimestopPng,
    'alert-flapping': lightIconAlertFlappingPng,
    'alert-handlers': lightIconAlertHandlersSvg,
    'alert-notify': lightIconAlertNotifyPng,
    'alert-notify-progress': lightIconAlertNotifyProgressPng,
    'alert-notify-result': lightIconAlertNotifyResultPng,
    'alert-ok': lightIconAlertOkPng,
    'alert-overview': lightIconAlertOverviewSvg,
    'alert-reload': lightIconAlertReloadPng,
    'alert-restart': lightIconAlertRestartPng,
    'alert-start': lightIconAlertStartPng,
    'alert-stop': lightIconAlertStopPng,
    'alert-timeline': lightIconAlertTimelineSvg,
    'alert-unknown': lightIconAlertUnknownPng,
    'alert-unreach': lightIconAlertUnreachPng,
    'alert-up': lightIconAlertUpPng,
    'alert-warn': lightIconAlertWarnPng,
    alerts: lightIconAlertsSvg,
    'all-states': lightIconAllStatesPng,
    analysis: lightIconAnalysisSvg,
    'analyze-config': lightIconAnalyzeConfigSvg,
    annotation: lightIconAnnotationPng,
    api: lightIconApiSvg,
    'app-monitoring-topic': lightIconAppMonitoringTopicSvg,
    apply: lightIconApplyPng,
    'ar-simulate': lightIconArSimulatePng,
    'archive-event': lightIconArchiveEventPng,
    'assume-0': lightIconAssume0Png,
    'assume-1': lightIconAssume1Png,
    'assume-2': lightIconAssume2Png,
    'assume-3': lightIconAssume3Png,
    'assume-bg': lightAssumeBgPng,
    'assume-none': lightIconAssumeNonePng,
    auditlog: lightIconAuditlogSvg,
    autherr: lightIconAutherrPng,
    authok: lightIconAuthokPng,
    'av-computation': lightIconAvComputationPng,
    availability: lightIconAvailabilitySvg,
    'aws-logo': lightIconAwsLogoSvg,
    'azure-storage': lightIconAzureStorageSvg,
    'azure-vms': lightIconAzureVmsSvg,
    back: lightIconBackPng,
    'back-off': lightIconBackOffPng,
    'background-job-details': lightIconBackgroundJobDetailsPng,
    'background-jobs': lightIconBackgroundJobsSvg,
    backup: lightIconBackupSvg,
    'backup-restore-stop': lightIconBackupRestoreStopPng,
    'backup-start': lightIconBackupStartPng,
    'backup-state': lightIconBackupStatePng,
    'backup-stop': lightIconBackupStopPng,
    'backup-target-edit': lightIconBackupTargetEditPng,
    'backup-targets': lightIconBackupTargetsSvg,
    bake: lightIconBakeSvg,
    'bake-result': lightIconBakeResultPng,
    barplot: lightIconBarplotSvg,
    'bi-freeze': lightIconBiFreezeSvg,
    bilist: lightIconBilistPng,
    bitree: lightIconBitreePng,
    'bookmark-list': lightIconBookmarkListSvg,
    bottom: lightIconBottomPng,
    bulk: lightIconBulkSvg,
    'bulk-import': lightIconBulkImportPng,
    cached: lightIconCachedPng,
    cancel: lightIconCancelSvg,
    'cannot-reschedule': lightIconCannotReschedulePng,
    certificate: lightIconCertificateSvg,
    check: lightIconCheckSvg,
    'check-parameters': lightIconCheckParametersSvg,
    'check-plugins': lightIconCheckPluginsSvg,
    checkbox: lightIconCheckboxSvg,
    'checkbox-hover-bg': lightCheckboxHoverBgPng,
    checkmark: lightIconCheckmarkSvg,
    'checkmark-bare': lightIconCheckmarkBareSvg,
    checkmk: lightIconCheckmkSvg,
    'checkmk-logo': lightIconCheckmkLogoSvg,
    'checkmk-logo-min': lightIconCheckmkLogoMinSvg,
    cleanup: lightIconCleanupPng,
    clear: lightIconClearPng,
    clipboard: lightIconClipboardSvg,
    clone: lightIconCloneSvg,
    clock: lightIconClockSvg,
    closetimewarp: lightIconClosetimewarpPng,
    cloud: lightIconCloudSvg,
    cluster: lightIconClusterPng,
    collapse: lightIconCollapsePng,
    'collapse-arrow': lightIconCollapseArrowPng,
    'color-mode': lightIconColorModeSvg,
    commands: lightIconCommandsSvg,
    condition: lightIconConditionPng,
    'connection-tests': lightIconConnectionTestsSvg,
    contactgroups: lightIconContactgroupsSvg,
    continue: lightIconContinuePng,
    copied: lightIconCopiedSvg,
    counting: lightIconCountingPng,
    crash: lightIconCrashSvg,
    'crash-glow': lightIconCrashGlowPng,
    'crit-problem': lightIconCritProblemSvg,
    critical: lightIconCriticalPng,
    cross: lightIconCrossSvg,
    'cross-grey': lightIconCrossGreySvg,
    'custom-attr': lightIconCustomAttrSvg,
    'custom-graph': lightIconCustomGraphPng,
    'custom-snapin': lightIconCustomSnapinSvg,
    'customer-management': lightIconCustomerManagementPng,
    d146n0571c5: lightIconD146n0571c5Png,
    dash: lightIconDashSvg,
    dashboard: lightIconDashboardSvg,
    'dashboard-controls': lightIconDashboardControlsPng,
    'dashboard-edit': lightIconDashboardEditSvg,
    'dashboard-main': lightIconDashboardMainSvg,
    'dashboard-problems': lightIconDashboardProblemsSvg,
    'dashboard-system': lightIconDashboardSystemSvg,
    'dashlet-anchor': lightDashletAnchorSvg,
    'dashlet-network-topology': lightIconDashletNetworkTopologyPng,
    'dashlet-nodata': lightIconDashletNodataPng,
    'dashlet-notifications-bar-chart': lightIconDashletNotificationsBarChartPng,
    'dashlet-resize': lightDashletResizeSvg,
    'dashlet-url': lightIconDashletUrlPng,
    'dcd-connections': lightIconDcdConnectionsSvg,
    'dcd-execute': lightIconDcdExecutePng,
    'dcd-history': lightIconDcdHistoryPng,
    delayed: lightIconDelayedPng,
    delete: lightIconDeleteSvg,
    'deploy-agents': lightIconDeployAgentsPng,
    'deployment-error': lightIconDeploymentErrorPng,
    'deployment-status': lightIconDeploymentStatusPng,
    'derived-downtime': lightIconDerivedDowntimePng,
    detail: lightIconDetailPng,
    'developer-resources': lightIconDeveloperResourcesSvg,
    diagnose: lightIconDiagnosePng,
    diagnostics: lightIconDiagnosticsSvg,
    'diagnostics-dump-file': lightIconDiagnosticsDumpFilePng,
    'disable-test': lightIconDisableTestPng,
    disabled: lightIconDisabledSvg,
    'disabled-service': lightIconDisabledServiceSvg,
    'dissolve-operation': lightIconDissolveOperationPng,
    docker: lightIconDockerSvg,
    down: lightIconDownPng,
    download: lightIconDownloadPng,
    'download-agents': lightIconDownloadAgentsSvg,
    'download-csv': lightIconDownloadCsvPng,
    'download-json': lightIconDownloadJsonPng,
    downtime: lightIconDowntimeSvg,
    'downtime-for-report': lightIconDowntimeForReportPng,
    edit: lightIconEditSvg,
    'edit-custom-graph': lightIconEditCustomGraphPng,
    'edit-forecast-model': lightIconEditForecastModelPng,
    email: lightIconEmailPng,
    empty: lightIconEmptyPng,
    'enable-test': lightIconEnableTestPng,
    enabled: lightIconEnabledPng,
    encrypted: lightIconEncryptedPng,
    end: lightIconEndPng,
    error: lightIconErrorPng,
    'event console-status': lightIconEventConsoleStatusSvg,
    event: lightIconEventSvg,
    'event-console': lightIconEventConsoleSvg,
    expand: lightIconExpandPng,
    export: lightIconExportPng,
    'export-rule': lightIconExportRuleSvg,
    factoryreset: lightIconFactoryresetPng,
    'fake-check-result': lightIconFakeCheckResultSvg,
    favicon: lightFaviconIco,
    filter: lightIconFilterSvg,
    'filters-set': lightIconFiltersSetPng,
    flapping: lightIconFlappingPng,
    folder: lightIconFolderSvg,
    'folder-closed': lightFolderClosedPng,
    'folder-hi': lightFolderHiPng,
    'folder-open': lightFolderOpenPng,
    folderproperties: lightIconFolderpropertiesPng,
    'forecast-graph': lightIconForecastGraphPng,
    'foreign-changes': lightIconForeignChangesPng,
    forth: lightIconForthPng,
    'forth-off': lightIconForthOffPng,
    frameurl: lightIconFrameurlSvg,
    gauge: lightIconGaugeSvg,
    gcp: lightIconGcpSvg,
    'global-settings': lightIconGlobalSettingsSvg,
    globe: lightGlobePng,
    graph: lightIconGraphSvg,
    'graph-collection': lightIconGraphCollectionPng,
    'graph-time': lightIconGraphTimeSvg,
    'graph-tuning': lightIconGraphTuningPng,
    'gui-design': lightIconGuiDesignPng,
    guitest: lightIconGuitestPng,
    'hard-states': lightIconHardStatesPng,
    hardware: lightIconHardwareSvg,
    hierarchy: lightIconHierarchySvg,
    history: lightIconHistoryPng,
    host: lightIconHostPng,
    'host-graph': lightIconHostGraphSvg,
    'host-problems': lightIconHostProblemsSvg,
    'host-state': lightIconHostStateSvg,
    'host-state-summary': lightIconHostStateSummarySvg,
    'host-statistics': lightIconHostStatisticsSvg,
    'host-svc-problems-dark': lightIconHostSvcProblemsDarkSvg,
    hostgroups: lightIconHostgroupsSvg,
    ical: lightIconIcalPng,
    icons: lightIconIconsSvg,
    ignore: lightIconIgnorePng,
    inactive: lightIconInactivePng,
    'influxdb-connections': lightIconInfluxdbConnectionsSvg,
    info: lightIconInfoSvg,
    'inline-error': lightIconInlineErrorSvg,
    insert: lightIconInsertSvg,
    insertdate: lightIconInsertdateSvg,
    install: lightIconInstallPng,
    'integrations-custom': lightIconIntegrationsCustomSvg,
    'integrations-other': lightIconIntegrationsOtherSvg,
    inv: lightIconInvPng,
    inventory: lightIconInventorySvg,
    'inventory-failed': lightIconInventoryFailedPng,
    inverted: lightIconInvertedPng,
    kubernetes: lightIconKubernetesSvg,
    'laptop-50': lightIconLaptop50Png,
    ldap: lightIconLdapSvg,
    'learning-beginner': lightIconLearningBeginnerSvg,
    'learning-checkmk': lightIconLearningCheckmkSvg,
    'learning-forum': lightIconLearningForumSvg,
    'learning-guide': lightIconLearningGuideSvg,
    'learning-video-tutorials': lightIconLearningVideoTutorialsSvg,
    'license-failed': lightIconLicenseFailedPng,
    'license-successful': lightIconLicenseSuccessfulPng,
    'license-unknown-state': lightIconLicenseUnknownStatePng,
    licensing: lightIconLicensingSvg,
    lightbulb: lightIconLightbulbSvg,
    'lightbulb-idea': lightIconLightbulbIdeaSvg,
    link: lightIconLinkPng,
    linux: lightIconLinuxSvg,
    'linux-deb': lightIconLinuxDebSvg,
    'linux-rpm': lightIconLinuxRpmSvg,
    'linux-tgz': lightIconLinuxTgzSvg,
    'load-graph': lightLoadGraphPng,
    localrule: lightIconLocalrulePng,
    log: lightIconLogSvg,
    login: lightIconLoginPng,
    'logo-cmk-small': lightLogoCmkSmallPng,
    logwatch: lightIconLogwatchPng,
    'magic-move': lightIconMagicMovePng,
    'main-changes-active': lightIconMainChangesActiveSvg,
    'main-customize-active': lightIconMainCustomizeActiveSvg,
    'main-help-active': lightIconMainHelpActiveSvg,
    'main-monitoring-active': lightIconMainMonitoringActiveSvg,
    'main-search-active': lightIconMainSearchActiveSvg,
    'main-setup-active': lightIconMainSetupActiveSvg,
    'main-user-active': lightIconMainUserActiveSvg,
    'manual-active': lightIconManualActiveSvg,
    matrix: lightIconMatrixPng,
    menu: lightIconMenuPng,
    'menu-item-checked': lightIconMenuItemCheckedPng,
    'menu-item-unchecked': lightIconMenuItemUncheckedPng,
    message: lightIconMessageSvg,
    'migrate-users': lightIconMigrateUsersSvg,
    missing: lightIconMissingSvg,
    'mkeventd-rules': lightIconMkeventdRulesPng,
    mkps: lightIconMkpsSvg,
    'monitored-service': lightIconMonitoredServiceSvg,
    move: lightIconMovePng,
    movedown: lightIconMovedownPng,
    moveup: lightIconMoveupPng,
    nagvis: lightIconNagvisPng,
    'need-replicate': lightIconNeedReplicatePng,
    'need-restart': lightIconNeedRestartPng,
    'network-services': lightIconNetworkServicesSvg,
    'network-topology': lightIconNetworkTopologySvg,
    networking: lightIconNetworkingSvg,
    new: lightIconNewSvg,
    'new-cluster': lightIconNewClusterPng,
    'new-mkp': lightIconNewMkpPng,
    newfolder: lightIconNewfolderPng,
    'no-entry': lightIconNoEntrySvg,
    'no-pending-changes': lightIconNoPendingChangesSvg,
    'no-revert': lightIconNoRevertSvg,
    nodowntime: lightIconNodowntimePng,
    notes: lightIconNotesPng,
    'notif-disabled': lightIconNotifDisabledPng,
    'notif-enabled': lightIconNotifEnabledPng,
    'notif-man-disabled': lightIconNotifManDisabledPng,
    'notification-enabled': lightIconNotificationEnabledPng,
    'notification-timeline': lightIconNotificationTimelineSvg,
    notifications: lightIconNotificationsSvg,
    npassive: lightIconNpassivePng,
    ntop: lightIconNtopSvg,
    ooservice: lightOoservicePng,
    'open-telemetry': lightIconOpenTelemetrySvg,
    opentelemetry: lightIconOpentelemetrySvg,
    'os-other': lightIconOsOtherSvg,
    'otel-collector': lightIconOtelCollectorSvg,
    'outof-serviceperiod': lightIconOutofServiceperiodPng,
    outofnot: lightIconOutofnotPng,
    packages: lightIconPackagesSvg,
    'pagetype-topic': lightIconPagetypeTopicSvg,
    pageurl: lightIconPageurlSvg,
    painteroptions: lightIconPainteroptionsSvg,
    'painteroptions-down-hi': lightIconPainteroptionsDownHiPng,
    'painteroptions-down-lo': lightIconPainteroptionsDownLoPng,
    'painteroptions-off': lightIconPainteroptionsOffPng,
    parentscan: lightIconParentscanPng,
    passwords: lightIconPasswordsSvg,
    pause: lightIconPausePng,
    'pending-changes': lightIconPendingChangesSvg,
    'pending-task': lightIconPendingTaskSvg,
    'percentage-of-service-problems': lightIconPercentageOfServiceProblemsSvg,
    persist: lightIconPersistPng,
    'pie-chart': lightIconPieChartPng,
    'plugins-agentless': lightIconPluginsAgentlessSvg,
    'plugins-app': lightIconPluginsAppPng,
    'plugins-cloud': lightIconPluginsCloudSvg,
    'plugins-containerization': lightIconPluginsContainerizationSvg,
    'plugins-generic': lightIconPluginsGenericSvg,
    'plugins-hw': lightIconPluginsHwPng,
    'plugins-os': lightIconPluginsOsSvg,
    'plugins-virtual': lightIconPluginsVirtualSvg,
    pluginurl: lightPluginurlPng,
    plus: lightIconPlusSvg,
    pnp: lightIconPnpPng,
    'predefined-conditions': lightIconPredefinedConditionsSvg,
    prediction: lightIconPredictionPng,
    problem: lightIconProblemSvg,
    prometheus: lightIconPrometheusSvg,
    'qs-aws': lightIconQsAwsSvg,
    'qs-azure': lightIconQsAzureSvg,
    'qs-gcp': lightIconQsGcpSvg,
    'qs-otel': lightIconQsOtelSvg,
    'qs-prometheus': lightIconQsPrometheusSvg,
    'qs-relay': lightIconQsRelaySvg,
    'quick-setup-aws': lightIconQuickSetupAwsSvg,
    quicksearch: lightIconQuicksearchPng,
    'quicksearch-field-bg': lightQuicksearchFieldBgPng,
    random: lightIconRandomPng,
    rank: lightIconRankSvg,
    'read-only': lightIconReadOnlySvg,
    'recreate-broker-certificate': lightIconRecreateBrokerCertificateSvg,
    redo: lightIconRedoSvg,
    'relay-menu': lightIconRelayMenuSvg,
    'release-deploy': lightReleaseDeploySvg,
    'release-mkp': lightIconReleaseMkpPng,
    'release-mkp-yellow': lightIconReleaseMkpYellowPng,
    'release-scale': lightReleaseScaleSvg,
    reload: lightIconReloadSvg,
    reloadsnapin: lightIconReloadsnapinPng,
    'reloadsnapin-lo-alt': lightIconReloadsnapinLoAltPng,
    'rename-host': lightIconRenameHostSvg,
    'repl-25': lightIconRepl25Png,
    'repl-50': lightIconRepl50Png,
    'repl-75': lightIconRepl75Png,
    'repl-failed': lightIconReplFailedPng,
    'repl-locked': lightIconReplLockedPng,
    'repl-pending': lightIconReplPendingPng,
    'repl-success': lightIconReplSuccessPng,
    replay: lightIconReplayPng,
    replicate: lightIconReplicatePng,
    report: lightIconReportSvg,
    'report-element': lightIconReportElementPng,
    'report-fixed': lightIconReportFixedPng,
    'report-store': lightIconReportStorePng,
    reportscheduler: lightIconReportschedulerPng,
    reset: lightIconResetPng,
    resetcounters: lightIconResetcountersPng,
    resize: lightIconResizePng,
    'resize-graph': lightResizeGraphPng,
    restart: lightIconRestartPng,
    restore: lightIconRestorePng,
    revert: lightIconRevertSvg,
    'rj45-50': lightIconRj4550Png,
    roles: lightIconRolesSvg,
    'rotate-left': lightIconRotateLeftPng,
    rule: lightIconRuleSvg,
    'rule-no': lightIconRuleNoPng,
    'rule-no-off': lightIconRuleNoOffPng,
    'rule-yes': lightIconRuleYesPng,
    'rule-yes-off': lightIconRuleYesOffPng,
    rules: lightIconRulesSvg,
    'rulesets-deprecated': lightIconRulesetsDeprecatedPng,
    'rulesets-ineffective': lightIconRulesetsIneffectivePng,
    saml: lightIconSamlSvg,
    save: lightIconSaveSvg,
    'save-dashboard': lightIconSaveDashboardSvg,
    'save-graph': lightIconSaveGraphSvg,
    'save-to-folder': lightIconSaveToFolderSvg,
    'save-to-services': lightIconSaveToServicesSvg,
    'save-view': lightIconSaveViewSvg,
    scatterplot: lightIconScatterplotSvg,
    'service-discovery': lightIconServiceDiscoverySvg,
    'service-duration': lightIconServiceDurationSvg,
    'service-graph': lightIconServiceGraphSvg,
    'service-label-add': lightIconServiceLabelAddSvg,
    'service-label-remove': lightIconServiceLabelRemoveSvg,
    'service-label-update': lightIconServiceLabelUpdateSvg,
    'service-state': lightIconServiceStateSvg,
    'service-to-disabled': lightIconServiceToDisabledSvg,
    'service-to-ignored': lightIconServiceToIgnoredSvg,
    'service-to-monitored': lightIconServiceToMonitoredSvg,
    'service-to-new': lightIconServiceToNewSvg,
    'service-to-removed': lightIconServiceToRemovedSvg,
    'service-to-unchanged': lightIconServiceToUnchangedSvg,
    'service-to-undecided': lightIconServiceToUndecidedSvg,
    servicegroups: lightIconServicegroupsSvg,
    services: lightIconServicesSvg,
    'services-fix-all': lightIconServicesFixAllSvg,
    'services-green': lightIconServicesGreenSvg,
    'services-refresh': lightIconServicesRefreshSvg,
    'services-stop': lightIconServicesStopPng,
    'services-tabula-rasa': lightIconServicesTabulaRasaSvg,
    'show-less-green': lightIconShowLessGreenSvg,
    'show-more-green': lightIconShowMoreGreenSvg,
    showbi: lightIconShowbiPng,
    showhide: lightIconShowhidePng,
    sidebar: lightIconSidebarSvg,
    'sidebar-logout': lightIconSidebarLogoutSvg,
    'sidebar-position': lightIconSidebarPositionSvg,
    'sidebar-top': lightSidebarTopPng,
    sign: lightIconSignSvg,
    'signature-key': lightIconSignatureKeySvg,
    'signature-key-partial': lightIconSignatureKeyPartialPng,
    'single-metric': lightIconSingleMetricSvg,
    'site-globals': lightIconSiteGlobalsPng,
    'site-globals-modified': lightIconSiteGlobalsModifiedPng,
    'site-overview': lightIconSiteOverviewSvg,
    sites: lightIconSitesSvg,
    sla: lightIconSlaSvg,
    'sla-configuration': lightIconSlaConfigurationPng,
    'snapin-greyswitch-off': lightIconSnapinGreyswitchOffPng,
    'snapin-greyswitch-on': lightIconSnapinGreyswitchOnPng,
    snapshot: lightIconSnapshotPng,
    'snapshot-checksum': lightIconSnapshotChecksumPng,
    'snapshot-nchecksum': lightIconSnapshotNchecksumPng,
    'snapshot-pchecksum': lightIconSnapshotPchecksumPng,
    snmp: lightIconSnmpSvg,
    software: lightIconSoftwareSvg,
    'solaris-pkg': lightIconSolarisPkgSvg,
    'solaris-tgz': lightIconSolarisTgzSvg,
    someproblem: lightSomeproblemPng,
    starred: lightIconStarredPng,
    start: lightIconStartPng,
    'static-checks': lightIconStaticChecksSvg,
    'static-text': lightIconStaticTextSvg,
    status: lightIconStatusSvg,
    'status-report': lightStatusReportPng,
    'svc-problems': lightIconSvcProblemsSvg,
    'sync-graphs': lightIconSyncGraphsPng,
    'sync-mkp': lightIconSyncMkpPng,
    'synthetic-monitoring-purple': lightIconSyntheticMonitoringPurpleSvg,
    'synthetic-monitoring-topic': lightIconSyntheticMonitoringTopicSvg,
    'synthetic-monitoring-yellow': lightIconSyntheticMonitoringYellowSvg,
    tag: lightIconTagSvg,
    timeline: lightIconTimelinePng,
    timeperiods: lightIconTimeperiodsSvg,
    timewarp: lightIconTimewarpPng,
    'timewarp-off': lightIconTimewarpOffPng,
    tls: lightIconTlsSvg,
    'toggle-context': lightIconToggleContextPng,
    'toggle-details': lightIconToggleDetailsPng,
    'toggle-on': lightIconToggleOnSvg,
    top: lightIconTopPng,
    'top-list': lightIconTopListSvg,
    'topic-2fa': lightIconTopic2faSvg,
    'topic-administration': lightIconTopicAdministrationPng,
    'topic-agents': lightIconTopicAgentsPng,
    'topic-analyze': lightIconTopicAnalyzePng,
    'topic-applications': lightIconTopicApplicationsPng,
    'topic-bi': lightIconTopicBiPng,
    'topic-change-password': lightIconTopicChangePasswordPng,
    'topic-checkmk': lightIconTopicCheckmkSvg,
    'topic-events': lightIconTopicEventsPng,
    'topic-exporter': lightIconTopicExporterSvg,
    'topic-general': lightIconTopicGeneralPng,
    'topic-graphs': lightIconTopicGraphsPng,
    'topic-history': lightIconTopicHistoryPng,
    'topic-hosts': lightIconTopicHostsPng,
    'topic-inventory': lightIconTopicInventoryPng,
    'topic-maintenance': lightIconTopicMaintenancePng,
    'topic-monitoring': lightIconTopicMonitoringSvg,
    'topic-my-workplace': lightIconTopicMyWorkplaceSvg,
    'topic-network': lightIconTopicNetworkSvg,
    'topic-other': lightIconTopicOtherPng,
    'topic-overview': lightIconTopicOverviewPng,
    'topic-problems': lightIconTopicProblemsPng,
    'topic-profile': lightIconTopicProfilePng,
    'topic-quick-setups': lightIconTopicQuickSetupsSvg,
    'topic-reporting': lightIconTopicReportingSvg,
    'topic-services': lightIconTopicServicesPng,
    'topic-site': lightIconTopicSitePng,
    'topic-system': lightIconTopicSystemSvg,
    'topic-user-interface': lightIconTopicUserInterfaceSvg,
    'topic-users': lightIconTopicUsersPng,
    'topic-visualization': lightIconTopicVisualizationPng,
    trans: lightIconTransSvg,
    trust: lightIconTrustPng,
    twofa: lightIcon2faSvg,
    'twofa-backup-codes': lightIcon2faBackupCodesSvg,
    'unacknowledge-test': lightIconUnacknowledgeTestPng,
    'undecided-service': lightIconUndecidedServiceSvg,
    undo: lightIconUndoSvg,
    'unpackaged-files': lightIconUnpackagedFilesPng,
    unusedbirules: lightIconUnusedbirulesPng,
    up: lightIconUpPng,
    update: lightIconUpdatePng,
    'update-discovery-parameters': lightIconUpdateDiscoveryParametersSvg,
    'update-host-labels': lightIconUpdateHostLabelsSvg,
    'update-service-labels': lightIconUpdateServiceLabelsSvg,
    upgrade: lightIconUpgradeSvg,
    upload: lightIconUploadPng,
    url: lightIconUrlPng,
    usedrulesets: lightIconUsedrulesetsPng,
    'user-locked': lightIconUserLockedPng,
    users: lightIconUsersSvg,
    'validation-error': lightIconValidationErrorPng,
    video: lightIconVideoPng,
    view: lightIconViewSvg,
    'view-columns': lightIconViewColumnsPng,
    'view-copy': lightIconViewCopySvg,
    'view-link': lightIconViewLinkSvg,
    'view-refresh': lightIconViewRefreshPng,
    vsphere: lightIconVsphereSvg,
    warning: lightIconWarningPng,
    wato: lightIconWatoPng,
    'wato-changes': lightIconWatoChangesPng,
    'wato-nochanges': lightIconWatoNochangesPng,
    'werk-ack': lightIconWerkAckPng,
    'widget-clone': lightIconWidgetCloneSvg,
    'widget-delete': lightIconWidgetDeleteSvg,
    'widget-edit': lightIconWidgetEditSvg,
    wikisearch: lightIconWikisearchPng,
    'windows-msi': lightIconWindowsMsiSvg,
    'wrong-agent': lightIconWrongAgentPng,
    www: lightIconWwwPng,
    zoom: lightIconZoomPng,
};

export const themedIcons: Record<string, Partial<Record<IconNames, string>>> = {
    light: {
        'add-rule': lightIconAddRuleSvg,
        'agent-registration': lightIconAgentRegistrationSvg,
        analyze: lightIconAnalyzeSvg,
        assign: lightIconAssignSvg,
        aws: lightIconAwsSvg,
        'cancel-notifications': lightIconCancelNotificationsSvg,
        'checkmark-bg-white': lightIconCheckmarkBgWhiteSvg,
        'checkmark-orange': lightIconCheckmarkOrangeSvg,
        'checkmark-plus': lightIconCheckmarkPlusSvg,
        close: lightIconCloseSvg,
        comment: lightIconCommentSvg,
        configuration: lightIconConfigurationSvg,
        'cross-bg-white': lightIconCrossBgWhiteSvg,
        'dashboard-grid': lightIconDashboardGridSvg,
        'dashboard-menuarrow': lightIconDashboardMenuarrowSvg,
        'dashlet-clone': lightDashletCloneSvg,
        'dashlet-delete': lightDashletDeleteSvg,
        'dashlet-edit': lightDashletEditSvg,
        drag: lightIconDragSvg,
        'export-link': lightIconExportLinkSvg,
        external: lightIconExternalSvg,
        favorite: lightIconFavoriteSvg,
        'filter-line': lightIconFilterLineSvg,
        fixall: lightIconFixallSvg,
        'folder-blue': lightIconFolderBlueSvg,
        help: lightIconHelpSvg,
        // icon_help_activated.svg is absent on CMK 2.3 and has no modern-dark
        // variant anywhere; reuse info-circle so the open-help icon never 404s.
        'help-activated': lightIconInfoCircleSvg,
        home: lightIconHomeSvg,
        'host-svc-problems': lightIconHostSvcProblemsSvg,
        hyphen: lightIconHyphenSvg,
        'info-circle': lightIconInfoCircleSvg,
        'main-changes': lightIconMainChangesSvg,
        'main-customize': lightIconMainCustomizeSvg,
        'main-help': lightIconMainHelpSvg,
        'main-monitoring': lightIconMainMonitoringSvg,
        'main-search': lightIconMainSearchSvg,
        'main-setup': lightIconMainSetupSvg,
        'main-user': lightIconMainUserSvg,
        manual: lightIconManualSvg,
        nagios: lightIconNagiosSvg,
        network: lightIconNetworkSvg,
        'performance-data': lightIconPerformanceDataSvg,
        'release-automated': lightReleaseAutomatedSvg,
        'reload-cmk': lightIconReloadCmkSvg,
        rulesets: lightIconRulesetsSvg,
        saas: lightIconSaasSvg,
        search: lightIconSearchSvg,
        'search-action': lightIconSearchActionSvg,
        'search-action-button': lightIconSearchActionButtonSvg,
        'select-arrow': lightIconSelectArrowSvg,
        'services-blue': lightIconServicesBlueSvg,
        'show-less': lightIconShowLessSvg,
        'show-more': lightIconShowMoreSvg,
        'sidebar-folded': lightIconSidebarFoldedSvg,
        'site-dead': lightIconSiteDeadSvg,
        'site-disabled': lightIconSiteDisabledSvg,
        'site-down': lightIconSiteDownSvg,
        'site-missing': lightIconSiteMissingSvg,
        'site-unreach': lightIconSiteUnreachSvg,
        'site-waiting': lightIconSiteWaitingSvg,
        snmpmib: lightIconSnmpmibSvg,
        sparkle: lightIconSparkleSvg,
        'sparkle-white': lightIconSparkleWhiteSvg,
        speedometer: lightSpeedometerSvg,
        stale: lightIconStaleSvg,
        suggestion: lightIconSuggestionSvg,
        'table-actions-off': lightIconTableActionsOffSvg,
        'table-actions-on': lightIconTableActionsOnSvg,
        tick: lightIconTickSvg,
        'toggle-off': lightIconToggleOffSvg,
        'tree-closed': lightIconTreeClosedSvg,
        qa: lightIconQaSvg,
        development: lightIconDevelopmentSvg,
        product: lightIconProductSvg,
        unavailable: lightIconUnavailableSvg,
        ux: lightIconUXSvg,
    },
    dark: {
        'add-rule': darkIconAddRuleSvg,
        'agent-registration': darkIconAgentRegistrationSvg,
        analyze: darkIconAnalyzeSvg,
        assign: darkIconAssignSvg,
        aws: darkIconAwsSvg,
        'cancel-notifications': darkIconCancelNotificationsSvg,
        'checkmark-bg-white': darkIconCheckmarkBgWhiteSvg,
        'checkmark-orange': darkIconCheckmarkOrangeSvg,
        'checkmark-plus': darkIconCheckmarkPlusSvg,
        close: darkIconCloseSvg,
        comment: darkIconCommentSvg,
        configuration: darkIconConfigurationSvg,
        'cross-bg-white': darkIconCrossBgWhiteSvg,
        'dashboard-grid': darkIconDashboardGridSvg,
        'dashboard-menuarrow': darkIconDashboardMenuarrowSvg,
        'dashlet-clone': darkDashletCloneSvg,
        'dashlet-delete': darkDashletDeleteSvg,
        'dashlet-edit': darkDashletEditSvg,
        drag: darkIconDragSvg,
        'export-link': darkIconExportLinkSvg,
        external: darkIconExternalSvg,
        favorite: darkIconFavoriteSvg,
        'filter-line': darkIconFilterLineSvg,
        fixall: darkIconFixallSvg,
        'folder-blue': darkIconFolderBlueSvg,
        help: darkIconHelpSvg,
        'help-activated': darkIconInfoCircleSvg,
        home: darkIconHomeSvg,
        'host-svc-problems': darkIconHostSvcProblemsSvg,
        hyphen: darkIconHyphenSvg,
        'info-circle': darkIconInfoCircleSvg,
        'main-changes': darkIconMainChangesSvg,
        'main-customize': darkIconMainCustomizeSvg,
        'main-help': darkIconMainHelpSvg,
        'main-monitoring': darkIconMainMonitoringSvg,
        'main-search': darkIconMainSearchSvg,
        'main-setup': darkIconMainSetupSvg,
        'main-user': darkIconMainUserSvg,
        manual: darkIconManualSvg,
        nagios: darkIconNagiosSvg,
        network: darkIconNetworkSvg,
        'performance-data': darkIconPerformanceDataSvg,
        'release-automated': darkReleaseAutomatedSvg,
        'reload-cmk': darkIconReloadCmkSvg,
        rulesets: darkIconRulesetsSvg,
        saas: darkIconSaasSvg,
        search: darkIconSearchSvg,
        'search-action': darkIconSearchActionSvg,
        'search-action-button': darkIconSearchActionButtonSvg,
        'select-arrow': darkIconSelectArrowSvg,
        'services-blue': darkIconServicesBlueSvg,
        'show-less': darkIconShowLessSvg,
        'show-more': darkIconShowMoreSvg,
        'sidebar-folded': darkIconSidebarFoldedSvg,
        'site-dead': darkIconSiteDeadSvg,
        'site-disabled': darkIconSiteDisabledSvg,
        'site-down': darkIconSiteDownSvg,
        'site-missing': darkIconSiteMissingSvg,
        'site-unreach': darkIconSiteUnreachSvg,
        'site-waiting': darkIconSiteWaitingSvg,
        snmpmib: darkIconSnmpmibSvg,
        sparkle: darkIconSparkleSvg,
        'sparkle-white': darkIconSparkleWhiteSvg,
        speedometer: darkSpeedometerSvg,
        stale: darkIconStaleSvg,
        suggestion: darkIconSuggestionSvg,
        'table-actions-off': darkIconTableActionsOffSvg,
        'table-actions-on': darkIconTableActionsOnSvg,
        tick: darkIconTickSvg,
        'toggle-off': darkIconToggleOffSvg,
        'tree-closed': darkIconTreeClosedSvg,
        qa: darkIconQaSvg,
        development: darkIconDevelopmentSvg,
        product: darkIconProductSvg,
        unavailable: darkIconUnavailableSvg,
        ux: darkIconUXSvg,
    },
};
