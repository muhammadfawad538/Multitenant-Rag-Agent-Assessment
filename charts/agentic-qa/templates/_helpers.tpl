{{/*
Expand the name of the chart.
*/}}
{{- define "agentic-qa.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "agentic-qa.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "agentic-qa.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "agentic-qa.labels" -}}
helm.sh/chart: {{ include "agentic-qa.chart" . }}
{{ include "agentic-qa.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
ai-engineer-assessment: "true"
architecture: "multitenant-rag-agentic"
deployment: "production"
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "agentic-qa.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agentic-qa.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "agentic-qa.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "agentic-qa.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Create image pull secret name
*/}}
{{- define "agentic-qa.imagePullSecretName" -}}
{{- if .Values.imagePullSecret.create -}}
    {{ default (printf "%s-registry" (include "agentic-qa.fullname" .)) .Values.imagePullSecret.name }}
{{- else -}}
    {{ default "" .Values.imagePullSecret.name }}
{{- end -}}
{{- end -}}

{{/*
Create environment variable string for Redis connection
*/}}
{{- define "agentic-qa.redisEnvVars" -}}
{{- if .Values.redis.enabled -}}
- name: REDIS_HOST
  value: {{ include "agentic-qa.fullname" . }}-redis
- name: REDIS_PORT
  value: "6379"
{{- if .Values.redis.auth.enabled -}}
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "agentic-qa.fullname" . }}-secrets
      key: redis-password
{{- end -}}
- name: REDIS_CACHE_ENABLED
  value: "true"
- name: REDIS_CACHE_TTL
  value: "3600"
{{- else -}}
- name: REDIS_CACHE_ENABLED
  value: "false"
{{- end -}}
{{- end -}}

{{/*
Create environment variable string for PostgreSQL connection
*/}}
{{- define "agentic-qa.postgresqlEnvVars" -}}
{{- if .Values.postgresql.enabled -}}
- name: POSTGRESQL_HOST
  value: {{ include "agentic-qa.fullname" . }}-postgresql
- name: POSTGRESQL_PORT
  value: "5432"
- name: POSTGRESQL_DATABASE
  valueFrom:
    secretKeyRef:
      name: {{ include "agentic-qa.fullname" . }}-secrets
      key: postgresql-database
- name: POSTGRESQL_USERNAME
  valueFrom:
    secretKeyRef:
      name: {{ include "agentic-qa.fullname" . }}-secrets
      key: postgresql-username
- name: POSTGRESQL_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "agentic-qa.fullname" . }}-secrets
      key: postgresql-password
- name: AUDIT_LOGGING_ENABLED
  value: "true"
{{- else -}}
- name: AUDIT_LOGGING_ENABLED
  value: "false"
{{- end -}}
{{- end -}}

{{/*
Create environment variable string for Qdrant connection
*/}}
{{- define "agentic-qa.qdrantEnvVars" -}}
{{- if .Values.qdrant.enabled -}}
- name: QDRANT_HOST
  value: {{ include "agentic-qa.fullname" . }}-qdrant
- name: QDRANT_PORT
  value: "6333"
- name: QDRANT_HTTP_PORT
  value: "6334"
- name: VECTOR_DB_ENABLED
  value: "true"
{{- if .Values.qdrant.apiKey -}}
- name: QDRANT_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "agentic-qa.fullname" . }}-secrets
      key: qdrant-api-key
{{- end -}}
{{- else -}}
- name: VECTOR_DB_ENABLED
  value: "false"
{{- end -}}
{{- end -}}

{{/*
Create a comma-separated list of enabled features
*/}}
{{- define "agentic-qa.enabledFeatures" -}}
{{- $features := list -}}
{{- if .Values.redis.enabled -}}
  {{- $features = append $features "redis-cache" -}}
{{- end -}}
{{- if .Values.postgresql.enabled -}}
  {{- $features = append $features "postgresql-audit" -}}
{{- end -}}
{{- if .Values.qdrant.enabled -}}
  {{- $features = append $features "qdrant-rag" -}}
{{- end -}}
{{- if .Values.metrics.enabled -}}
  {{- $features = append $features "prometheus-metrics" -}}
{{- end -}}
{{- if .Values.ingress.enabled -}}
  {{- $features = append $features "ingress-external" -}}
{{- end -}}
{{- join "," $features -}}
{{- end -}}

{{/*
Create the name for the network policy
*/}}
{{- define "agentic-qa.networkPolicyName" -}}
{{- printf "%s-network-policy" (include "agentic-qa.fullname" .) -}}
{{- end -}}

{{/*
Create the name for the service monitor
*/}}
{{- define "agentic-qa.serviceMonitorName" -}}
{{- printf "%s-service-monitor" (include "agentic-qa.fullname" .) -}}
{{- end -}}