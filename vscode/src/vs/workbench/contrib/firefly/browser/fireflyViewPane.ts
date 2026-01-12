/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { ViewPane, IViewPaneOptions } from '../../../browser/parts/views/viewPane.js';
import './media/firefly.css';
import { IKeybindingService } from '../../../../platform/keybinding/common/keybinding.js';
import { IContextMenuService } from '../../../../platform/contextview/browser/contextView.js';
import { IConfigurationService } from '../../../../platform/configuration/common/configuration.js';
import { IContextKeyService } from '../../../../platform/contextkey/common/contextkey.js';
import { IViewDescriptorService } from '../../../common/views.js';
import { IInstantiationService } from '../../../../platform/instantiation/common/instantiation.js';
import { IOpenerService } from '../../../../platform/opener/common/opener.js';
import { IThemeService } from '../../../../platform/theme/common/themeService.js';
import { IHoverService } from '../../../../platform/hover/browser/hover.js';
import { IFireflyWorkbenchService } from '../../../services/firefly/common/firefly.js';
import { IQuickInputService } from '../../../../platform/quickinput/common/quickInput.js';
import { append, $, addDisposableListener } from '../../../../base/browser/dom.js';

export class FireflyViewPane extends ViewPane {

    private container?: HTMLElement;
    private thoughtElement?: HTMLElement;

    private costElement?: HTMLElement;
    private statusTag?: HTMLElement;
    private autonomousBtn?: HTMLButtonElement;

    constructor(
        options: IViewPaneOptions,
        @IKeybindingService keybindingService: IKeybindingService,
        @IContextMenuService contextMenuService: IContextMenuService,
        @IConfigurationService configurationService: IConfigurationService,
        @IContextKeyService contextKeyService: IContextKeyService,
        @IViewDescriptorService viewDescriptorService: IViewDescriptorService,
        @IInstantiationService instantiationService: IInstantiationService,
        @IOpenerService openerService: IOpenerService,
        @IThemeService themeService: IThemeService,
        @IHoverService hoverService: IHoverService,
        @IQuickInputService private readonly quickInputService: IQuickInputService,
        @IFireflyWorkbenchService private readonly fireflyService: IFireflyWorkbenchService
    ) {
        super(options, keybindingService, contextMenuService, configurationService, contextKeyService, viewDescriptorService, instantiationService, openerService, themeService, hoverService);
    }

    protected override renderBody(container: HTMLElement): void {
        super.renderBody(container);

        this.container = append(container, $('.firefly-agent-hub'));

        // Premium Header
        const header = append(this.container, $('.firefly-header'));
        append(header, $('.firefly-title')).textContent = 'Agent Hub';
        this.statusTag = append(header, $('.firefly-status-tag.online'));
        this.statusTag.textContent = 'Connected';

        // Agent List Section
        append(this.container, $('.firefly-section-label')).textContent = 'Active Agents';
        const agentList = append(this.container, $('.firefly-agent-list'));

        // Mock Agents based on Mockup
        this.renderAgentCard(agentList, 'Reviewer', 'codicon-sparkle', 'Analyzing architectural patterns...', true);
        this.renderAgentCard(agentList, 'Coder', 'codicon-terminal', 'Implementing feature X...', false);
        this.renderAgentCard(agentList, 'Architect', 'codicon-layers', 'Idle', false);

        // Global Thought/Activity (Linked to real backend)
        append(this.container, $('.firefly-section-label')).textContent = 'Firefly Pulse';
        const pulseCard = append(this.container, $('.firefly-agent-card.active'));
        const pulseHeader = append(pulseCard, $('.agent-card-header'));
        append(pulseHeader, $('.agent-icon.codicon.codicon-radio-tower'));
        append(pulseHeader, $('.agent-name')).textContent = 'Primary Link';
        append(pulseHeader, $('.agent-status-indicator'));

        // Thought Stream (Scrollable)
        this.thoughtElement = append(this.container, $('.firefly-thought-stream'));

        // Controls
        append(this.container, $('.firefly-section-label')).textContent = 'Directives';
        const controls = append(this.container, $('.firefly-controls'));
        this.autonomousBtn = append(controls, $('button.firefly-button')) as HTMLButtonElement;
        const createBtn = append(controls, $('button.firefly-button.create-btn')) as HTMLButtonElement;
        createBtn.textContent = 'Create Agent';
        append(createBtn, $('.codicon.codicon-add'));

        this._register(addDisposableListener(createBtn, 'click', async () => {
            const name = await this.quickInputService.input({
                prompt: 'Summon Generic Agent',
                placeHolder: 'e.g., Reviewer, Coder, Architect',
                title: 'Firefly: Summon New Intelligence'
            });
            if (name) {
                const persona = await this.quickInputService.input({
                    prompt: 'Define Agent Persona',
                    placeHolder: 'e.g., Expert in TypeScript and Clean Architecture',
                    title: `Firefly: Define ${name}`
                });
                if (persona) {
                    await this.fireflyService.createAgent(name, persona);
                }
            }
        }));

        this.updateAutonomousButton();

        if (this.autonomousBtn) {
            this._register(addDisposableListener(this.autonomousBtn, 'click', () => {
                const current = this.fireflyService.isAutonomousMode();
                this.fireflyService.setAutonomousMode(!current);
            }));
        }

        // Model & Safety Controls Section
        append(this.container, $('.firefly-section-label')).textContent = 'Orchestration';
        const orchestrationControls = append(this.container, $('.firefly-controls'));

        // Model Selector Button
        const modelBtn = append(orchestrationControls, $('button.firefly-button'));
        append(modelBtn, $('span.codicon.codicon-hubot'));
        append(modelBtn, $('span')).textContent = ` ${this.getModelDisplayName(this.fireflyService.getActiveModel())}`;

        this._register(addDisposableListener(modelBtn, 'click', async () => {
            const models = this.fireflyService.getAvailableModels();
            const picks = models.map(m => ({
                label: m.name,
                description: m.provider,
                id: m.id
            }));

            const selected = await this.quickInputService.pick(picks, {
                placeHolder: 'Select AI Model',
                title: 'Firefly: Model Orchestration'
            });

            if (selected) {
                this.fireflyService.setActiveModel((selected as any).id);
                modelBtn.innerText = '';
                append(modelBtn, $('span.codicon.codicon-hubot'));
                append(modelBtn, $('span')).textContent = ` ${selected.label}`;
            }
        }));

        // Safety Mode Button
        const safetyBtn = append(orchestrationControls, $('button.firefly-button'));
        append(safetyBtn, $('span.codicon.codicon-shield'));
        append(safetyBtn, $('span')).textContent = ` ${this.fireflyService.getSafetyMode()}`;

        this._register(addDisposableListener(safetyBtn, 'click', async () => {
            const modes = [
                { label: 'AUTO', description: 'Maximum speed. Most commands auto-approved.' },
                { label: 'ORCHESTRATOR_ONLY', description: 'Lead agent commands auto-approved.' },
                { label: 'MANUAL', description: 'Every command requires approval.' }
            ];

            const selected = await this.quickInputService.pick(modes, {
                placeHolder: 'Select Safety Mode',
                title: 'Firefly: Command Approval Mode'
            });

            if (selected) {
                this.fireflyService.setSafetyMode(selected.label as any);
                safetyBtn.innerText = '';
                append(safetyBtn, $('span.codicon.codicon-shield'));
                append(safetyBtn, $('span')).textContent = ` ${selected.label}`;
            }
        }));

        // Usage Investment
        this.costElement = append(this.container, $('.firefly-usage-container'));

        // Chat Input
        const chatContainer = append(this.container, $('.firefly-chat-container'));
        const chatInput = append(chatContainer, $<HTMLInputElement>('input.firefly-chat-input'));
        chatInput.placeholder = 'Message Firefly...';
        chatInput.type = 'text';

        this._register(addDisposableListener(chatInput, 'keydown', (e: KeyboardEvent) => {
            if (e.key === 'Enter' && chatInput.value.trim()) {
                const text = chatInput.value.trim();
                this.fireflyService.sendChat(text);
                // Optimistically add to view (or rely on history update if service persists it?)
                // Service doesn't persist USER chats automatically unless we call reportIntent or similar?
                // Actually reportIntent appends observation. 
                // We should add a method to service to append USER CHAT thought.
                // But for now let's just send it.
                // Wait, if I want it in the stream, the service needs to know.
                // I'll update the service to append the thought in sendChat.
                chatInput.value = '';
            }
        }));

        this.updateStatus();

        // Listen for updates
        this._register(this.fireflyService.onDidChangeThought(() => this.updateThought()));
        this._register(this.fireflyService.onDidChangeStatus(() => this.updateStatus()));
        this._register(this.fireflyService.onDidChangeMode(() => {
            this.updateAutonomousButton();
            this.updateStatus();
        }));
        this._register(this.fireflyService.onDidChangeActiveModel((modelId) => {
            modelBtn.innerText = '';
            append(modelBtn, $('span.codicon.codicon-hubot'));
            append(modelBtn, $('span')).textContent = ` ${this.getModelDisplayName(modelId)}`;
        }));
        this._register(this.fireflyService.onDidChangeSafetyMode((mode) => {
            safetyBtn.innerText = '';
            append(safetyBtn, $('span.codicon.codicon-shield'));
            append(safetyBtn, $('span')).textContent = ` ${mode}`;
        }));

        this.updateThought();
    }

    private getModelDisplayName(modelId: string): string {
        const models = this.fireflyService.getAvailableModels();
        const model = models.find(m => m.id === modelId);
        return model?.name || modelId;
    }

    private renderAgentCard(parent: HTMLElement, name: string, icon: string, status: string, isActive: boolean): void {
        const card = append(parent, $(`.firefly-agent-card${isActive ? '.active' : ''}`));
        const header = append(card, $('.agent-card-header'));
        append(header, $(`.agent-icon.codicon.${icon}`));
        const nameEl = append(header, $('.agent-name'));
        nameEl.textContent = name;

        if (isActive) {
            append(header, $('.agent-status-indicator'));
        }

        const body = append(card, $('.agent-card-body'));
        body.textContent = status;

        this._register(addDisposableListener(card, 'click', () => {
            // Remove active from all
            parent.querySelectorAll('.firefly-agent-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');

            // Update Primary Link Title
            const pulseTitle = this.container?.querySelector('.firefly-agent-card.active .agent-name');
            if (pulseTitle) {
                pulseTitle.textContent = `${name} Link`;
            }
        }));
    }

    private updateThought(): void {
        if (!this.thoughtElement) {
            return;
        }

        const history = this.fireflyService.getThoughtHistory();

        // Clear current view (inefficient but safe for now, better to append diffs later)
        // Actually, let's just re-render all for simplicity as history is capped at 100
        // Clear current view
        this.thoughtElement.innerText = '';

        if (history.length === 0) {
            const empty = append(this.thoughtElement, $('.thought-item.observation'));
            empty.textContent = 'Observing workspace...';
            return;
        }

        history.forEach(t => {
            const el = append(this.thoughtElement!, $(`.thought-item.${t.type}`));
            // Add icon based on type
            let icon = 'codicon-eye';
            if (t.type === 'reasoning') icon = 'codicon-lightbulb';
            if (t.type === 'action') icon = 'codicon-tools';

            append(el, $(`.thought-icon.codicon.${icon}`));
            const textSpan = append(el, $('.thought-content'));
            textSpan.textContent = t.text;
        });

        // Auto-scroll
        this.thoughtElement.scrollTop = this.thoughtElement.scrollHeight;
    }

    private updateStatus(): void {
        if (this.costElement) {
            const cost = this.fireflyService.getTotalCost();
            this.costElement.innerText = '';
            append(this.costElement, $('span.firefly-section-label')).textContent = 'Investment';
            append(this.costElement, $('span.firefly-cost')).textContent = ` $${cost.toFixed(4)}`;
        }

        if (this.statusTag) {
            const isAutonomous = this.fireflyService.isAutonomousMode();
            this.statusTag.className = `firefly-status-tag online ${isAutonomous ? 'autonomous' : ''}`;
            this.statusTag.textContent = isAutonomous ? 'Autonomous' : 'Connected';
        }
    }

    private updateAutonomousButton(): void {
        if (this.autonomousBtn) {
            const isAutonomous = this.fireflyService.isAutonomousMode();
            this.autonomousBtn.innerText = '';
            append(this.autonomousBtn, $('span')).textContent = `${isAutonomous ? 'Pause' : 'Engage'} `;
            append(this.autonomousBtn, $(`span.codicon.codicon-${isAutonomous ? 'debug-pause' : 'rocket'}`));
            this.autonomousBtn.className = `firefly-button ${isAutonomous ? 'active' : ''}`;
        }
    }
}
