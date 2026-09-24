/**
 * Copyright (c) 2025, WSO2 LLC. (https://www.wso2.com).
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

/**
 * Per-field character limits for console form inputs.
 *
 * These exist so a single oversized field cannot push a request past the
 * 64 KB body limit of the AWS WAF in front of the cloud and on-prem
 * deployments: the WAF drops such a request before the service sees it, and
 * the user gets a bare 403 with no field to blame.
 * Enforcing the limit at the input means the user sees the cap while typing
 * instead of discovering it on submit.
 *
 * Counts are characters, not bytes. A non-ASCII character can serialise to
 * up to 4 bytes, so a field's byte cost can be several times its character
 * count. The caps are per field, so a form that fills several large fields
 * can still exceed the WAF limit.
 */
export const INPUT_LIMITS = {
  /** Generated/URL-safe handles (agent name, scope name, role handle). */
  HANDLE: 50,
  /** Human-facing names and display names. */
  NAME: 100,
  /** Single-line free text: titles, labels, summaries. */
  SHORT_TEXT: 255,
  /**
   * Description fields across every create/edit form, including the markdown
   * ones. Generous enough for a few paragraphs of prose with formatting, and
   * still far below the WAF body limit.
   */
  DESCRIPTION: 2_000,
  /** Multi-line free text that is expected to be long: README, instructions. */
  LONG_TEXT: 8_000,
  /** Prompts and markdown documents authored in the console. */
  PROMPT: 16_000,
  /** Source code authored in the console (evaluator bodies, config editors). */
  SOURCE: 32_000,
  /**
   * Name of a mounted file. 253 is the Kubernetes ConfigMap/Secret key limit,
   * which is what the agent form's schema validates against; the shared
   * FileMountEditor caps at the same value so it cannot refuse a name the
   * schema would accept.
   */
  FILE_NAME: 253,
  /**
   * Contents of a mounted config file, matching the 1 MB the backend and the
   * agent form's schema accept. Where a WAF sits in front of the platform, a
   * file over its 64 KB body limit is still rejected there.
   */
  FILE_CONTENT: 1_048_576,
  /** URLs and endpoints. */
  URL: 2_048,
  /** Environment variable / header / parameter keys. */
  KEY: 128,
  /** Environment variable / header / parameter values. */
  VALUE: 4_096,
  /** Filesystem-ish paths handed to the build container. */
  PATH: 512,
  /** Secrets, API keys and tokens pasted into the console. */
  SECRET: 4_096,
  /** Passwords typed into the console. */
  PASSWORD: 128,
} as const;

export type InputLimit = (typeof INPUT_LIMITS)[keyof typeof INPUT_LIMITS];
