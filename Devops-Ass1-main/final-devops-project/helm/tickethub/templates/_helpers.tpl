{{- define "tickethub.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "tickethub.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "tickethub.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "tickethub.labels" -}}
app.kubernetes.io/name: {{ include "tickethub.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: tickethub
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
owner: vansh
{{- end -}}

{{- define "tickethub.databaseUrl" -}}
postgresql+psycopg://{{ .Values.postgres.user }}:$(POSTGRES_PASSWORD)@{{ .Release.Name }}-postgres:5432/{{ .Values.postgres.database }}
{{- end -}}
