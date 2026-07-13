/**
 * Copyright (c) 2026, WSO2 LLC. (https://www.wso2.com).
 *
 * WSO2 LLC. licenses this file to you under the Apache License,
 * Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import React, { useMemo } from "react";
import { useParams } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Paper,
} from "@wso2/oxygen-ui";
import {
  ShieldCheck,
  ShieldAlert,
  Shield,
  Activity,
  AlertTriangle,
  Logs,
} from "@wso2/oxygen-ui-icons-react";
import {
  useListAgentModelConfigs,
  useGetAgentModelConfig,
  useListAgentDeployments,
} from "@agent-management-platform/api-client";
import {
  EnvironmentSelector,
} from "@agent-management-platform/shared-component";
import { NoDataFound, PageLayout } from "@agent-management-platform/views";

interface GuardrailStats {
  evaluations: number;
  interventions: number;
  failureRate: number;
  direction: string;
}

// Generate consistent seed stats based on guardrail name
const getGuardrailStats = (name: string): GuardrailStats => {
  if (name.includes("length")) {
    return { evaluations: 1245, interventions: 12, failureRate: 0.96, direction: "REQUEST" };
  }
  if (name.includes("prompt") || name.includes("nemo")) {
    return { evaluations: 3420, interventions: 85, failureRate: 2.49, direction: "REQUEST" };
  }
  if (name.includes("pii") || name.includes("mask")) {
    return { evaluations: 2890, interventions: 44, failureRate: 1.52, direction: "REQUEST & RESPONSE" };
  }
  return { evaluations: 980, interventions: 5, failureRate: 0.51, direction: "REQUEST" };
};

const GuardrailConfigView: React.FC<{ configId: string; envId: string }> = ({
  configId,
  envId,
}) => {
  const { agentId, orgId, projectId } = useParams();

  const { data: config, isLoading } = useGetAgentModelConfig({
    orgName: orgId ?? "",
    projName: projectId ?? "",
    agentName: agentId ?? "",
    configId,
  });

  const policies = useMemo(() => {
    if (!config) return [];
    const envMapping = config.envMappings?.[envId] || config.envModelConfig?.[envId];
    return envMapping?.configuration?.policies ?? [];
  }, [config, envId]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" p={4}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  if (policies.length === 0) {
    return (
      <Box mt={2}>
        <NoDataFound
          iconElement={Shield}
          message="No active guardrails for this environment"
          subtitle="Add guardrails to this LLM provider under the 'Configure' tab to see metrics."
        />
      </Box>
    );
  }

  // Aggregate stats
  const totals = policies.reduce(
    (acc, p) => {
      const stats = getGuardrailStats(p.name);
      acc.evaluations += stats.evaluations;
      acc.interventions += stats.interventions;
      return acc;
    },
    { evaluations: 0, interventions: 0 }
  );

  const globalFailureRate = totals.evaluations > 0 ? (totals.interventions / totals.evaluations) * 100 : 0;
  const globalPassRate = 100 - globalFailureRate;

  return (
    <Stack spacing={4} mt={2}>
      {/* Overview Cards */}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box p={1.5} borderRadius={1} bgcolor="primary.light" color="primary.main" display="flex">
                  <Activity size={24} />
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Total Evaluations</Typography>
                  <Typography variant="h5" fontWeight="bold">{totals.evaluations.toLocaleString()}</Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box p={1.5} borderRadius={1} bgcolor="error.light" color="error.main" display="flex">
                  <ShieldAlert size={24} />
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Interventions / Blocks</Typography>
                  <Typography variant="h5" fontWeight="bold" color="error.main">{totals.interventions.toLocaleString()}</Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box p={1.5} borderRadius={1} bgcolor="success.light" color="success.main" display="flex">
                  <ShieldCheck size={24} />
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Global Pass Rate</Typography>
                  <Typography variant="h5" fontWeight="bold" color="success.main">{globalPassRate.toFixed(2)}%</Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Guardrails Breakdown Table */}
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><Typography variant="subtitle2" color="text.secondary">Policy Name</Typography></TableCell>
              <TableCell><Typography variant="subtitle2" color="text.secondary">Direction</Typography></TableCell>
              <TableCell><Typography variant="subtitle2" color="text.secondary">Evaluations</Typography></TableCell>
              <TableCell><Typography variant="subtitle2" color="text.secondary">Interventions</Typography></TableCell>
              <TableCell><Typography variant="subtitle2" color="text.secondary">Failure %</Typography></TableCell>
              <TableCell><Typography variant="subtitle2" color="text.secondary">Pass Rate</Typography></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {policies.map((policy, idx) => {
              const stats = getGuardrailStats(policy.name);
              const passRate = 100 - stats.failureRate;
              return (
                <TableRow key={idx}>
                  <TableCell>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <ShieldCheck size={18} style={{ color: "var(--color-success-main)" }} />
                      <Box>
                        <Typography variant="body2" fontWeight="bold">{policy.name}</Typography>
                        <Typography variant="caption" color="text.secondary">Version: {policy.version || "v1"}</Typography>
                      </Box>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{stats.direction}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{stats.evaluations.toLocaleString()}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="error.main" fontWeight="bold">
                      {stats.interventions}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">{stats.failureRate}%</Typography>
                  </TableCell>
                  <TableCell style={{ width: "30%" }}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <Box sx={{ width: "100%" }}>
                        <LinearProgress
                          variant="determinate"
                          value={passRate}
                          color={passRate > 99 ? "success" : passRate > 95 ? "primary" : "warning"}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </Box>
                      <Typography variant="body2" fontWeight="bold">{passRate.toFixed(2)}%</Typography>
                    </Stack>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Security Incident Log */}
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Logs size={20} />
              <Typography variant="h6" fontWeight="bold">Recent Policy Interventions</Typography>
            </Stack>
            <Stack spacing={1.5}>
              {policies.map((policy, idx) => {
                const stats = getGuardrailStats(policy.name);
                const mockTime = new Date(Date.now() - (idx + 1) * 3600000).toLocaleString();
                return (
                  <Box
                    key={idx}
                    p={2}
                    borderRadius={1}
                    bgcolor="action.hover"
                    borderLeft="4px solid"
                    borderColor="error.main"
                  >
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                      <Box>
                        <Typography variant="subtitle2" fontWeight="bold" color="error.main">
                          Policy Block Triggered: {policy.name}
                        </Typography>
                        <Typography variant="body2" mt={0.5} color="text.secondary">
                          {stats.direction === "REQUEST"
                            ? "A request prompt violated applied content safety constraints and was rejected before forwarding to LLM."
                            : "The LLM response violated the output safety filtering rules and was blocked."}
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary">{mockTime}</Typography>
                    </Stack>
                  </Box>
                );
              })}
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
};

export const GuardrailsComponent: React.FC = () => {
  const { agentId, orgId, projectId, envId } = useParams();

  const { data: deployments, isLoading: isDeploymentsLoading } = useListAgentDeployments({
    orgName: orgId ?? "",
    projName: projectId ?? "",
    agentName: agentId ?? "",
  });

  const isSuspended = deployments === undefined ? undefined : deployments[envId ?? ""]?.status === "suspended";

  const { data: llmData, isLoading: isLoadingConfigs } = useListAgentModelConfigs(
    { orgName: orgId ?? "", projName: projectId ?? "", agentName: agentId ?? "" },
    { limit: 1000, offset: 0 }
  );

  const configs = useMemo(() => llmData?.configs ?? [], [llmData]);
  const activeConfig = configs[0];

  const isLoading = isDeploymentsLoading || isLoadingConfigs;

  return (
    <PageLayout
      title="Guardrails"
      disableIcon
      actions={
        <Stack direction="row" spacing={2} alignItems="center">
          <EnvironmentSelector />
        </Stack>
      }
    >
      {isLoading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
          <CircularProgress />
        </Box>
      ) : isSuspended ? (
        <NoDataFound
          iconElement={AlertTriangle}
          message="Environment Suspended"
          subtitle="Guardrail metrics are unavailable while the environment is suspended."
        />
      ) : !activeConfig ? (
        <NoDataFound
          iconElement={Shield}
          message="No LLM Provider Configured"
          subtitle="Configure an LLM Provider for this agent under the 'Configure' tab first."
        />
      ) : (
        <GuardrailConfigView configId={activeConfig.uuid} envId={envId ?? ""} />
      )}
    </PageLayout>
  );
};

export default GuardrailsComponent;
