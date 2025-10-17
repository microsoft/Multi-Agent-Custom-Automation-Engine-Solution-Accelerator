import {

  AgentType,
  ProcessedPlanData,
  MPlanData,
  StepStatus,
  WebsocketMessageType,
  ParsedUserClarification,
  AgentMessageType,
  PlanFromAPI,
  AgentMessageData,
  AgentMessageBE,
  StartingTaskBE,
  StartingTask,
  TeamAgentBE,
  Agent,
  TeamConfig,
  TeamConfigurationBE,
  MPlanBE,
  MStepBE,
  AgentMessageResponse,
  FinalMessage,
  StreamingMessage,
  UserRequestObject
} from "@/models";
import { apiService } from "@/api";

/**
 * Service for processing and managing plan data operations
 */
export class PlanDataService {
  /**
   * Fetch plan details by plan ID and process the data
   * @param planId Plan ID to fetch
   * @returns Promise with processed plan data
   */
  static async fetchPlanData(
    planId: string,
    useCache: boolean
  ): Promise<ProcessedPlanData> {
    try {
      // Use optimized getPlanById method for better performance
      const planBody = await apiService.getPlanById(planId, useCache);
      console.log('Raw plan data fetched:', planBody);
      return this.processPlanData(planBody);
    } catch (error) {
      console.log("Failed to fetch plan data:", error);
      throw error;
    }
  }

  /**
   * Process plan data to extract agents, steps, and clarification status
   * @param plan PlanWithSteps object to process
   * @returns Processed plan data
   */
  /**
 * Converts AgentMessageBE array to AgentMessageData array
 * @param messages - Array of AgentMessageBE from backend
 * @returns Array of AgentMessageData or empty array if input is null/empty
 */
  static convertAgentMessages(messages: AgentMessageBE[]): AgentMessageData[] {
    if (!messages || messages.length === 0) {
      return [];
    }

    return messages.map((message: AgentMessageBE): AgentMessageData => ({
      agent: message.agent,
      agent_type: message.agent_type,
      timestamp: message.timestamp ? new Date(message.timestamp).getTime() : Date.now(),
      steps: message.steps || [],
      next_steps: message.next_steps ?? [],
      content: message.content,
      raw_data: message.raw_data
    }));
  }

  /**
   * Converts TeamConfigurationBE to TeamConfig
   * @param teamConfigBE - TeamConfigurationBE from backend
   * @returns TeamConfig or null if input is null/undefined
   */
  static convertTeamConfiguration(teamConfigBE: TeamConfigurationBE | null): TeamConfig | null {
    if (!teamConfigBE) {
      return null;
    }

    return {
      id: teamConfigBE.id,
      team_id: teamConfigBE.team_id,
      name: teamConfigBE.name,
      description: teamConfigBE.description || '',
      status: teamConfigBE.status as 'visible' | 'hidden',
      protected: false, // Default value since it's not in TeamConfigurationBE
      created: teamConfigBE.created,
      created_by: teamConfigBE.created_by,
      logo: teamConfigBE.logo || '',
      plan: teamConfigBE.plan || '',
      agents: teamConfigBE.agents.map((agentBE: TeamAgentBE): Agent => ({
        input_key: agentBE.input_key,
        type: agentBE.type,
        name: agentBE.name,
        deployment_name: agentBE.deployment_name,
        system_message: agentBE.system_message,
        description: agentBE.description,
        icon: agentBE.icon,
        index_name: agentBE.index_name,
        use_rag: agentBE.use_rag,
        use_mcp: agentBE.use_mcp,
        coding_tools: agentBE.coding_tools,
        // Additional fields that exist in Agent but not in TeamAgentBE
        index_endpoint: undefined,
        id: undefined,
        capabilities: undefined,
        role: undefined
      })),
      starting_tasks: teamConfigBE.starting_tasks.map((taskBE: StartingTaskBE): StartingTask => ({
        id: taskBE.id,
        name: taskBE.name,
        prompt: taskBE.prompt,
        created: taskBE.created,
        creator: taskBE.creator,
        logo: taskBE.logo
      }))
    };
  }
  /**
  * Extracts the actual text from a user_request object or string
  * @param userRequest - Either a string or UserRequestObject
  * @returns The extracted text string
  */
  static extractUserRequestText(userRequest: string | UserRequestObject): string {
    if (typeof userRequest === 'string') {
      return userRequest;
    }

    if (userRequest && typeof userRequest === 'object') {
      // Look for text in the items array
      if (Array.isArray(userRequest.items)) {
        const textItem = userRequest.items.find(item => item.text);
        if (textItem?.text) {
          return textItem.text;
        }
      }

      // Fallback: try to find any text content
      if (userRequest.content_type === 'text' && 'text' in userRequest) {
        return (userRequest as any).text || '';
      }

      // Last resort: stringify the object
      return JSON.stringify(userRequest);
    }

    return '';
  }

  /**
   * Converts MPlanBE to MPlanData
   * @param mplanBE - MPlanBE from backend
   * @returns MPlanData or null if input is null/undefined
   */
  static convertMPlan(mplanBE: MPlanBE | null): MPlanData | null {
    if (!mplanBE) {
      return null;
    }

    // Extract the actual user request text
    const userRequestText = this.extractUserRequestText(mplanBE.user_request);

    // Convert MStepBE[] to the MPlanData steps format
    const steps = mplanBE.steps.map((stepBE: MStepBE, index: number) => ({
      id: index + 1, // MPlanData expects numeric id starting from 1
      action: stepBE.action,
      cleanAction: stepBE.action
        .replace(/\*\*/g, '') // Remove markdown bold
        .replace(/^Certainly!\s*/i, '')
        .replace(/^Given the team composition and the available facts,?\s*/i, '')
        .replace(/^here is a (?:concise )?plan to[^.]*\.\s*/i, '')
        .replace(/^\*\*([^*]+)\*\*:?\s*/g, '$1: ')
        .replace(/^[-•]\s*/, '')
        .replace(/\s+/g, ' ')
        .trim(),
      agent: stepBE.agent
    }));

    return {
      id: mplanBE.id,
      status: mplanBE.overall_status.toString().toUpperCase(),
      user_request: userRequestText,
      team: mplanBE.team,
      facts: mplanBE.facts,
      steps: steps,
      context: {
        task: userRequestText,
        participant_descriptions: {} // Default empty object since it's not in MPlanBE
      },
      // Additional fields from m_plan
      user_id: mplanBE.user_id,
      team_id: mplanBE.team_id,
      plan_id: mplanBE.plan_id,
      overall_status: mplanBE.overall_status.toString(),
      raw_data: mplanBE // Store the original object as raw_data
    };
  }
  static processPlanData(planFromAPI: PlanFromAPI): ProcessedPlanData {
    // Extract unique agents from steps

    const plan = planFromAPI.plan;
    const team = this.convertTeamConfiguration(planFromAPI.team);
    const mplan = this.convertMPlan(planFromAPI.m_plan);
    const messages: AgentMessageData[] = this.convertAgentMessages(planFromAPI.messages || []);
    const streaming_message = planFromAPI.streaming_message || null;
    return {
      plan,
      team,
      mplan,
      messages,
      streaming_message
    };
  }

  /**
 * Converts AgentMessageData to AgentMessageResponse using ProcessedPlanData context
 * @param agentMessage - AgentMessageData to convert
 * @param planData - ProcessedPlanData for context (plan_id, user_id, etc.)
 * @returns AgentMessageResponse
 */
  static createAgentMessageResponse(
    agentMessage: AgentMessageData,
    planData: ProcessedPlanData,
    is_final: boolean = false,
    streaming_message: string = ''
  ): AgentMessageResponse {
    if (!planData || !planData.plan) {
      console.log("Invalid plan data provided to createAgentMessageResponse");
    }
    return {
      plan_id: planData.plan.plan_id,
      agent: agentMessage.agent,
      content: agentMessage.content,
      agent_type: agentMessage.agent_type,
      is_final: is_final,
      raw_data: JSON.stringify(agentMessage.raw_data),
      streaming_message: streaming_message
    };
  }

  /**
   * Submit human clarification for a plan
   * @param planId Plan ID
   * @param sessionId Session ID
   * @param clarification Clarification text
   * @returns Promise with API response
   */
  static async submitClarification({
    request_id,
    answer,
    plan_id,
    m_plan_id
  }: {
    request_id: string;
    answer: string;
    plan_id: string;
    m_plan_id: string;
  }) {
    try {
      return apiService.submitClarification(request_id, answer, plan_id, m_plan_id);
    } catch (error) {
      console.log("Failed to submit clarification:", error);
      throw error;
    }
  }

  static parsePlanApprovalRequest(rawData: any): MPlanData | null {
    try {
      if (!rawData) return null;

      // Normalize to the PlanApprovalRequest(...) string that contains MPlan(...)
      let source: string | null = null;

      if (typeof rawData === 'object') {
        if (typeof rawData.data === 'string' && /PlanApprovalRequest\(plan=MPlan\(/.test(rawData.data)) {
          source = rawData.data;
        } else if (rawData.plan && typeof rawData.plan === 'object') {
          // Already structured style
          const mplan = rawData.plan;
          const userRequestText =
            typeof mplan.user_request === 'string'
              ? mplan.user_request
              : (Array.isArray(mplan.user_request?.items)
                ? (mplan.user_request.items.find((i: any) => i.text)?.text || '')
                : (mplan.user_request?.content || '')
              ).replace?.(/\u200b/g, '').trim() || 'Plan approval required';

          const steps = (mplan.steps || []).map((step: any, i: number) => {
            const action = step.action || '';
            const cleanAction = action
              .replace(/\*\*/g, '')
              .replace(/^Certainly!\s*/i, '')
              .replace(/^Given the team composition and the available facts,?\s*/i, '')
              .replace(/^here is a (?:concise )?plan[^.]*\.\s*/i, '')
              .replace(/^(?:here is|this is) a (?:concise )?(?:plan|approach|strategy)[^.]*[.:]\s*/i, '')
              .replace(/^\*\*([^*]+)\*\*:?\s*/g, '$1: ')
              .replace(/^[-•]\s*/, '')
              .replace(/\s+/g, ' ')
              .trim();
            return {
              id: i + 1,
              action,
              cleanAction,
              agent: step.agent || step._agent || 'System'
            };
          }).filter((s: any) => s.cleanAction.length > 3 && !/^(?:involvement|certainly|given|here is)/i.test(s.cleanAction));


          const result: MPlanData = {
            id: mplan.id || mplan.plan_id || 'unknown',
            status: (mplan.overall_status || rawData.status || 'PENDING_APPROVAL').toString().toUpperCase(),
            user_request: userRequestText,
            team: Array.isArray(mplan.team) ? mplan.team : [],
            facts: mplan.facts || '',
            steps,
            context: {
              task: userRequestText,
              participant_descriptions: rawData.context?.participant_descriptions || {}
            },
            user_id: mplan.user_id,
            team_id: mplan.team_id,
            plan_id: mplan.plan_id,
            overall_status: mplan.overall_status,
            raw_data: rawData
          };
          return result;
        }
      } else if (typeof rawData === 'string') {
        if (/PlanApprovalRequest\(plan=MPlan\(/.test(rawData)) {
          source = rawData;
        } else if (/^MPlan\(/.test(rawData)) {
          source = `PlanApprovalRequest(plan=${rawData})`;
        }
      }

      if (!source) return null;

      // Extract inner MPlan body
      const mplanMatch =
        source.match(/plan=MPlan\(([\s\S]*?)\),\s*status=/) ||
        source.match(/plan=MPlan\(([\s\S]*?)\)\s*\)/);
      const body = mplanMatch ? mplanMatch[1] : null;
      if (!body) return null;

      const pick = (re: RegExp, upper = false): string | undefined => {
        const m = body.match(re);
        return m ? (upper ? m[1].toUpperCase() : m[1]) : undefined;
      };

      const id = pick(/id='([^']+)'/) || pick(/id="([^"]+)"/) || 'unknown';
      const user_id = pick(/user_id='([^']*)'/) || '';
      const team_id = pick(/team_id='([^']*)'/) || '';
      const plan_id = pick(/plan_id='([^']*)'/) || '';
      let overall_status =
        pick(/overall_status=<PlanStatus\.([a-zA-Z_]+):/, true) ||
        pick(/overall_status='([^']+)'/, true) ||
        'PENDING_APPROVAL';

      const outerStatus =
        source.match(/status='([^']+)'/)?.[1] ||
        source.match(/status="([^"]+)"/)?.[1];
      const status = (outerStatus || overall_status || 'PENDING_APPROVAL').toUpperCase();

      let user_request =
        source.match(/text='([^']+)'/)?.[1] ||
        source.match(/text="([^"]+)"/)?.[1] ||
        'Plan approval required';
      user_request = user_request.replace(/\\u200b/g, '').trim();

      const teamRaw = body.match(/team=\[([^\]]*)\]/)?.[1] || '';
      const team = teamRaw
        .split(',')
        .map(s => s.trim().replace(/['"]/g, ''))
        .filter(Boolean);

      const facts =
        body
          .match(/facts="((?:[^"\\]|\\.)*)"/)?.[1]
          ?.replace(/\\n/g, '\n')
          .replace(/\\"/g, '"') || '';

      const steps: MPlanData['steps'] = [];
      const stepRegex = /MStep\(([^)]*?)\)/g;
      let stepMatch: RegExpExecArray | null;
      let idx = 1;
      const seen = new Set<string>();
      while ((stepMatch = stepRegex.exec(body)) !== null) {
        const chunk = stepMatch[1];
        const agent =
          chunk.match(/agent='([^']+)'/)?.[1] ||
          chunk.match(/agent="([^"]+)"/)?.[1] ||
          'System';
        const actionRaw =
          chunk.match(/action='([^']+)'/)?.[1] ||
          chunk.match(/action="([^"]+)"/)?.[1] ||
          '';
        if (!actionRaw) continue;

        const cleanAction = actionRaw
          .replace(/\*\*/g, '')
          .replace(/^Certainly!\s*/i, '')
          .replace(/^Given the team composition and the available facts,?\s*/i, '')
          .replace(/^here is a (?:concise )?plan to[^.]*\.\s*/i, '')
          .replace(/^\*\*([^*]+)\*\*:?\s*/g, '$1: ')
          .replace(/^[-•]\s*/, '')
          .replace(/\s+/g, ' ')
          .trim();

        const key = cleanAction.toLowerCase();
        if (
          cleanAction.length > 3 &&
          !seen.has(key) &&
          !/^(?:here is|this is|given|certainly|involvement)$/i.test(cleanAction)
        ) {
          seen.add(key);
          steps.push({
            id: idx++,
            action: actionRaw,
            cleanAction,
            agent
          });
        }
      }

      let participant_descriptions: Record<string, string> = {};
      const pdMatch =
        source.match(/participant_descriptions['"]?\s*:\s*({[^}]*})/) ||
        source.match(/'participant_descriptions':\s*({[^}]*})/);
      if (pdMatch?.[1]) {
        const jsonish = pdMatch[1]
          .replace(/'/g, '"')
          .replace(/([a-zA-Z0-9_]+)\s*:/g, '"$1":');
        try {
          participant_descriptions = JSON.parse(jsonish);
        } catch {
          participant_descriptions = {};
        }
      }

      const result: MPlanData = {
        id,
        status,
        user_request,
        team,
        facts,
        steps,
        context: {
          task: user_request,
          participant_descriptions
        },
        user_id,
        team_id,
        plan_id,
        overall_status,
        raw_data: rawData
      };

      return result;
    } catch (e) {
      console.error('parsePlanApprovalRequest failed:', e);
      return null;
    }
  }

  /**
   * Parse an agent message object or repr string:
   * Input forms supported:
   *  - { type: 'agent_message', data: "AgentMessage(agent_name='X', timestamp=..., content='...')"}
   *  - { type: 'agent_message', data: { agent_name: 'X', timestamp: 12345, content: '...' } }
   *  - "AgentMessage(agent_name='X', timestamp=..., content='...')"
   * Returns a structured object with steps parsed from markdown-ish content.
   */
  static parseAgentMessage(rawData: any): {
    agent: string;
    agent_type: AgentMessageType;
    timestamp: number | null;
    steps: Array<{
      title: string;
      fields: Record<string, string>;
      summary?: string;
      raw_block: string;
    }>;
    next_steps: string[];
    content: string;
    raw_data: any;
  } | null {
    try {
      // Handle JSON string input - parse it first
      if (typeof rawData === 'string' && rawData.startsWith('{')) {
        try {
          rawData = JSON.parse(rawData);
        } catch (e) {
          console.error('Failed to parse JSON string:', e);
          // Fall through to handle as regular string
        }
      }

      // Unwrap wrapper - handle object format
      if (rawData && typeof rawData === 'object' && rawData.type === WebsocketMessageType.AGENT_MESSAGE) {
        if (typeof rawData.data === 'object' && rawData.data.agent_name) {
          // New format: { type: 'agent_message', data: { agent_name: '...', timestamp: 123, content: '...' } }
          const data = rawData.data;
          const content = data.content || '';
          const timestamp = typeof data.timestamp === 'number' ? data.timestamp : null;

          // Parse the content for steps and next_steps (reuse existing logic)
          const { steps, next_steps } = this.parseContentForStepsAndNextSteps(content);

          return {
            agent: data.agent_name || 'UnknownAgent',
            agent_type: AgentMessageType.AI_AGENT,
            timestamp,
            steps,
            next_steps,
            content,
            raw_data: rawData
          };
        } else if (typeof rawData.data === 'string') {
          // Old format: { type: 'agent_message', data: "AgentMessage(...)" }
          return this.parseAgentMessage(rawData.data);
        }
      }

      // Handle direct object format
      if (rawData && typeof rawData === 'object' && rawData.agent_name) {
        const content = rawData.content || '';
        const timestamp = typeof rawData.timestamp === 'number' ? rawData.timestamp : null;

        // Parse the content for steps and next_steps
        const { steps, next_steps } = this.parseContentForStepsAndNextSteps(content);

        return {
          agent: rawData.agent_name || 'UnknownAgent',
          agent_type: AgentMessageType.AI_AGENT,
          timestamp,
          steps,
          next_steps,
          content,
          raw_data: rawData
        };
      }

      // Handle old string format: "AgentMessage(...)"
      if (typeof rawData !== 'string') return null;
      if (!rawData.startsWith('AgentMessage(')) return null;

      const source = rawData;

      const agent =
        source.match(/agent_name='([^']+)'/)?.[1] ||
        source.match(/agent_name="([^"]+)"/)?.[1] ||
        'UnknownAgent';

      const timestampStr =
        source.match(/timestamp=([\d.]+)/)?.[1];
      const timestamp = timestampStr ? Number(timestampStr) : null;

      // Extract content='...'
      const contentMatch = source.match(/content='((?:\\'|[^'])*)'/);
      let content = contentMatch ? contentMatch[1] : '';
      // Unescape
      content = content
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\');

      // Parse the content for steps and next_steps
      const { steps, next_steps } = this.parseContentForStepsAndNextSteps(content);

      return {
        agent,
        agent_type: AgentMessageType.AI_AGENT,
        timestamp,
        steps,
        next_steps,
        content,
        raw_data: rawData
      };
    } catch (e) {
      console.error('Failed to parse agent message:', e);
      return null;
    }
  }

  /**
   * Helper method to parse content for steps and next_steps
   * Extracted to avoid code duplication
   */
  private static parseContentForStepsAndNextSteps(content: string): {
    steps: Array<{
      title: string;
      fields: Record<string, string>;
      summary?: string;
      raw_block: string;
    }>;
    next_steps: string[];
  } {
    // Parse sections of the form "##### Title Completed"
    // Each block ends at --- line or next "##### " or end.
    const lines = content.split('\n');
    const steps: Array<{ title: string; fields: Record<string, string>; summary?: string; raw_block: string; }> = [];
    let i = 0;
    while (i < lines.length) {
      const headingMatch = lines[i].match(/^#####\s+(.+?)\s+Completed\s*$/i);
      if (headingMatch) {
        const title = headingMatch[1].trim();
        const blockLines: string[] = [];
        i++;
        while (i < lines.length && !/^---\s*$/.test(lines[i]) && !/^#####\s+/.test(lines[i])) {
          blockLines.push(lines[i]);
          i++;
        }
        // Skip separator line if present
        if (i < lines.length && /^---\s*$/.test(lines[i])) i++;

        const fields: Record<string, string> = {};
        let summary: string | undefined;
        for (const bl of blockLines) {
          const fieldMatch = bl.match(/^\*\*(.+?)\*\*:\s*(.*)$/);
          if (fieldMatch) {
            const fieldName = fieldMatch[1].trim().replace(/:$/, '');
            const value = fieldMatch[2].trim().replace(/\\s+$/, '');
            if (fieldName) fields[fieldName] = value;
          } else {
            const summaryMatch = bl.match(/^AGENT SUMMARY:\s*(.+)$/i);
            if (summaryMatch) {
              summary = summaryMatch[1].trim();
            }
          }
        }

        steps.push({
          title,
          fields,
          summary,
          raw_block: blockLines.join('\n').trim()
        });
      } else {
        i++;
      }
    }

    // Next Steps section
    const next_steps: string[] = [];
    const nextIdx = lines.findIndex(l => /^Next Steps:/.test(l.trim()));
    if (nextIdx !== -1) {
      for (let j = nextIdx + 1; j < lines.length; j++) {
        const l = lines[j].trim();
        if (!l) continue;
        if (/^[-*]\s+/.test(l)) {
          next_steps.push(l.replace(/^[-*]\s+/, '').trim());
        }
      }
    }

    return { steps, next_steps };
  }

  /**
   * Parse streaming agent message fragments.
   * Supports:
   *  - { type: 'agent_message_streaming', data: "AgentMessageStreaming(agent_name='X', content='partial', is_final=False)" }
   *  - { type: 'agent_message_streaming', data: { agent_name: 'X', content: 'partial', is_final: true } }
   *  - "AgentMessageStreaming(agent_name='X', content='partial', is_final=False)"
   */
  static parseAgentMessageStreaming(rawData: any): StreamingMessage | null {
    try {
      // Handle JSON string input - parse it first
      if (typeof rawData === 'string' && rawData.startsWith('{')) {
        try {
          rawData = JSON.parse(rawData);
        } catch (e) {
          console.error('Failed to parse JSON string:', e);
          // Fall through to handle as regular string
        }
      }

      // Unwrap wrapper - handle object format
      if (rawData && typeof rawData === 'object' && rawData.type === 'agent_message_streaming') {
        if (typeof rawData.data === 'object' && rawData.data.agent_name) {
          // New format: { type: 'agent_message_streaming', data: { agent_name: '...', content: '...', is_final: true } }
          const data = rawData.data;
          return {
            type: WebsocketMessageType.AGENT_MESSAGE_STREAMING,
            agent: data.agent_name || 'UnknownAgent',
            content: data.content || '',
            is_final: Boolean(data.is_final),
            raw_data: rawData
          };
        } else if (typeof rawData.data === 'string') {
          // Old format: { type: 'agent_message_streaming', data: "AgentMessageStreaming(...)" }
          return this.parseAgentMessageStreaming(rawData.data);
        }
      }

      // Handle direct object format
      if (rawData && typeof rawData === 'object' && rawData.agent_name) {
        return {
          type: WebsocketMessageType.AGENT_MESSAGE_STREAMING,
          agent: rawData.agent_name || 'UnknownAgent',
          content: rawData.content || '',
          is_final: Boolean(rawData.is_final),
          raw_data: rawData
        };
      }

      // Handle old string format: "AgentMessageStreaming(...)"
      if (typeof rawData !== 'string') return null;
      if (!rawData.startsWith('AgentMessageStreaming(')) return null;

      const source = rawData;

      const agent =
        source.match(/agent_name='([^']+)'/)?.[1] ||
        source.match(/agent_name="([^"]+)"/)?.[1] ||
        'UnknownAgent';

      const contentMatch = source.match(/content='((?:\\'|[^'])*)'/);
      let content = contentMatch ? contentMatch[1] : '';
      content = content
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\');

      let is_final = false;
      const finalMatch = source.match(/is_final=(True|False)/i);
      if (finalMatch) {
        is_final = /True/i.test(finalMatch[1]);
      }

      return {
        type: WebsocketMessageType.AGENT_MESSAGE_STREAMING,
        agent, content, is_final, raw_data: rawData
      };
    } catch (e) {
      console.error('Failed to parse streaming agent message:', e);
      return null;
    }
  }
  // ...inside export class PlanDataService { (place near other parsers, e.g. after parseAgentMessageStreaming)

  /**
   * Parse a user clarification request message (possibly deeply nested).
   * Accepts objects like:
   * {
   *   type: 'user_clarification_request',
   *   data: { type: 'user_clarification_request', data: { type: 'user_clarification_request', data: "UserClarificationRequest(...)" } }
   * }
   * Returns ParsedUserClarification or null if not parsable.
   */
  // ...existing code...
  /**
   * Parse a user clarification request message (possibly deeply nested).
   * Enhanced to support:
   *  - question in single OR double quotes
   *  - request_id in single OR double quotes
   *  - escaped newline / quote sequences
   */
  static parseUserClarificationRequest(rawData: any): ParsedUserClarification | null {
    try {
      const extractString = (val: any, depth = 0): string | null => {
        if (depth > 15) return null;
        if (typeof val === 'string') {
          return val.startsWith('UserClarificationRequest(') ? val : null;
        }
        if (val && typeof val === 'object') {
          // Prefer .data traversal
          if (val.data !== undefined) {
            const inner = extractString(val.data, depth + 1);
            if (inner) return inner;
          }
          for (const k of Object.keys(val)) {
            if (k === 'data') continue;
            const inner = extractString(val[k], depth + 1);
            if (inner) return inner;
          }
        }
        return null;
      };

      const source = extractString(rawData);
      if (!source) return null;

      // question=( "...") OR ('...')
      const questionRegex = /question=(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')/;
      const qMatch = source.match(questionRegex);
      if (!qMatch) return null;

      let question = (qMatch[1] ?? qMatch[2] ?? '')
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\')
        .trim();

      // request_id='uuid' or "uuid"
      const requestIdRegex = /request_id=(?:"([a-fA-F0-9-]+)"|'([a-fA-F0-9-]+)')/;
      const rMatch = source.match(requestIdRegex);
      if (!rMatch) return null;
      const request_id = rMatch[1] ?? rMatch[2];

      return {
        type: WebsocketMessageType.USER_CLARIFICATION_REQUEST,
        question,
        request_id
      };
    } catch (e) {
      console.error('parseUserClarificationRequest failed:', e);
      return null;
    }
  }
  // ...inside export class PlanDataService (place near other parsers) ...

  /**
   * Parse a final result message (possibly nested).
   * Accepts structures like:
   * {
   *   type: 'final_result_message',
   *   data: { type: 'final_result_message', data: { content: '...', status: 'completed', timestamp: 12345.6 } }
   * }
   * Returns null if not parsable.
   */
  static parseFinalResultMessage(rawData: any): FinalMessage | null {
    try {
      const extractPayload = (val: any, depth = 0): any => {
        if (depth > 10) return null;
        if (!val || typeof val !== 'object') return null;
        // If it has content & status, assume it's the payload
        if (('content' in val) && ('status' in val)) return val;
        if ('data' in val) {
          const inner = extractPayload(val.data, depth + 1);
          if (inner) return inner;
        }
        // Scan other keys as fallback
        for (const k of Object.keys(val)) {
          if (k === 'data') continue;
          const inner = extractPayload(val[k], depth + 1);
          if (inner) return inner;
        }
        return null;
      };

      const payload = extractPayload(rawData);
      if (!payload) return null;

      let content = typeof payload.content === 'string' ? payload.content : '';
      content = content
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\')
        .trim();

      const statusRaw = (payload.status || 'completed').toString().trim();
      const status = statusRaw.toLowerCase();

      let timestamp: number | null = null;
      if (payload.timestamp != null) {
        const num = Number(payload.timestamp);
        if (!Number.isNaN(num)) timestamp = num;
      }

      return {
        type: WebsocketMessageType.FINAL_RESULT_MESSAGE,
        content,
        status,
        timestamp,
        raw_data: rawData
      };
    } catch (e) {
      console.error('parseFinalResultMessage failed:', e);
      return null;
    }
  }

  static simplifyHumanClarification(line: string): string {
    if (
      typeof line !== 'string' ||
      !line.includes('Human clarification:') ||
      !line.includes('UserClarificationResponse(')
    ) {
      return line;
    }

    // Capture the inside of UserClarificationResponse(...)
    const outerMatch = line.match(/Human clarification:\s*UserClarificationResponse\((.*)\)$/s);
    if (!outerMatch) return line;

    const inner = outerMatch[1];

    // Find answer= '...' | "..." - Updated regex to handle the full content properly
    const answerMatch = inner.match(/answer='([^']*(?:''[^']*)*)'/);
    if (!answerMatch) {
      // Try double quotes if single quotes don't work
      const doubleQuoteMatch = inner.match(/answer="([^"]*(?:""[^"]*)*)"/);
      if (!doubleQuoteMatch) return line;

      let answer = doubleQuoteMatch[1];
      answer = answer
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\')
        .trim();

      return `Human clarification: ${answer}`;
    }

    let answer = answerMatch[1];
    // Unescape common sequences
    answer = answer
      .replace(/\\n/g, '\n')
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\')
      .trim();

    return `Human clarification: ${answer}`;
  }
}