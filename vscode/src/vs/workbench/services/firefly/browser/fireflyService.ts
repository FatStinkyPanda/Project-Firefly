/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { IFireflyWorkbenchService, IFireflyThought, SafetyMode, IModelUsage } from '../common/firefly.js';
import { Disposable } from '../../../../base/common/lifecycle.js';
import { Emitter } from '../../../../base/common/event.js';
import { ILogService } from '../../../../platform/log/common/log.js';
import { registerSingleton, InstantiationType } from '../../../../platform/instantiation/common/extensions.js';
import { IMainProcessService } from '../../../../platform/ipc/common/mainProcessService.js';
import { FireflyChannelClient } from '../../../../platform/firefly/common/fireflyIpc.js';

export class FireflyWorkbenchService extends Disposable implements IFireflyWorkbenchService {

    readonly _serviceBrand: undefined;

    private readonly _onDidChangeThought = this._register(new Emitter<IFireflyThought>());
    readonly onDidChangeThought = this._onDidChangeThought.event;

    private readonly _onDidChangeStatus = this._register(new Emitter<void>());
    readonly onDidChangeStatus = this._onDidChangeStatus.event;

    private readonly _onDidChangeMode = this._register(new Emitter<boolean>());
    readonly onDidChangeMode = this._onDidChangeMode.event;

    private readonly _onDidChangeSafetyMode = this._register(new Emitter<SafetyMode>());
    readonly onDidChangeSafetyMode = this._onDidChangeSafetyMode.event;

    private readonly _onDidChangeActiveModel = this._register(new Emitter<string>());
    readonly onDidChangeActiveModel = this._onDidChangeActiveModel.event;

    private _isAutonomousMode: boolean = false;
    private _currentThought?: IFireflyThought;
    private _totalCost: number = 0;
    private _safetyMode: SafetyMode = 'MANUAL';
    private _activeModel: string = 'gemini-2.0-flash';
    private _modelUsage: IModelUsage[] = [];
    private _client: FireflyChannelClient;
    private _thoughtHistory: IFireflyThought[] = [];

    private readonly _availableModels = [
        { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', provider: 'Google' },
        { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google' },
        { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
        { id: 'claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic' },
        { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
        { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
        { id: 'llama-3.1-70b', name: 'Llama 3.1 70B', provider: 'Local/Ollama' }
    ];

    constructor(
        @ILogService private readonly logService: ILogService,
        @IMainProcessService private readonly mainProcessService: IMainProcessService
    ) {
        super();
        this.logService.info('[Firefly] Workbench Service Online.');

        this._client = new FireflyChannelClient(this.mainProcessService.getChannel('firefly'));

        this._register(this._client.onDidStatusChange(status => {
            if (status.currentThought && (!this._currentThought || status.currentThought !== this._currentThought.text)) {
                this.appendThought({ text: status.currentThought, type: 'reasoning' });
            }

            if (status.totalCost !== undefined && status.totalCost !== this._totalCost) {
                this._totalCost = status.totalCost;
                this._onDidChangeStatus.fire();
            }

            if (status.isAutonomous !== undefined && status.isAutonomous !== this._isAutonomousMode) {
                this._isAutonomousMode = status.isAutonomous;
                this._onDidChangeMode.fire(this._isAutonomousMode);
            }
        }));

        this._client.getStatus().then(status => {
            this._totalCost = status.totalCost;
            this._isAutonomousMode = status.isAutonomous;
            if (status.currentThought) {
                this.appendThought({ text: status.currentThought, type: 'reasoning' });
            }
            this._onDidChangeStatus.fire();
            this._onDidChangeMode.fire(this._isAutonomousMode);
        });
    }

    isAutonomousMode(): boolean {
        return this._isAutonomousMode;
    }

    setAutonomousMode(enabled: boolean): void {
        if (this._isAutonomousMode !== enabled) {
            this._isAutonomousMode = enabled;
            this._onDidChangeMode.fire(enabled);
            this._client.setAutonomousMode(enabled);
            this.logService.info(`[Firefly] Autonomous Mode: ${enabled ? 'ENABLED' : 'DISABLED'}`);
        }
    }

    getCurrentThought(): IFireflyThought | undefined {
        return this._currentThought;
    }

    getTotalCost(): number {
        return this._totalCost;
    }

    reportIntent(id: string, args: unknown[]): void {
        this.logService.trace(`[Firefly] Observed User Intent: ${id}`, args);
        this._client.sendIntent(id, args as any[]);

        this.appendThought({ text: `User invoked ${id}`, type: 'observation' });
    }

    private appendThought(thought: IFireflyThought): void {
        this._currentThought = thought;
        this._thoughtHistory.push(thought);
        // Keep last 100 thoughts
        if (this._thoughtHistory.length > 100) {
            this._thoughtHistory.shift();
        }
        this._onDidChangeThought.fire(thought);
    }

    getThoughtHistory(): IFireflyThought[] {
        return this._thoughtHistory;
    }

    async createAgent(name: string, persona: string): Promise<string> {
        this.logService.info(`[Firefly] Frontend requested agent creation: ${name}`);
        return this._client.createAgent(name, persona);
    }

    async deleteAgent(id: string): Promise<void> {
        this.logService.info(`[Firefly] Frontend requested agent deletion: ${id}`);
        return this._client.deleteAgent(id);
    }

    // Safety Mode Controls
    getSafetyMode(): SafetyMode {
        return this._safetyMode;
    }

    setSafetyMode(mode: SafetyMode): void {
        if (this._safetyMode !== mode) {
            this._safetyMode = mode;
            this._onDidChangeSafetyMode.fire(mode);
            this._client.setSafetyMode(mode);
            this.logService.info(`[Firefly] Safety Mode: ${mode}`);
        }
    }

    async sendChat(text: string): Promise<void> {
        this.appendThought({ text: `User: ${text}`, type: 'user-chat' });
        return this._client.sendChat(text);
    }

    // Model Orchestration
    getActiveModel(): string {
        return this._activeModel;
    }

    setActiveModel(modelId: string): void {
        if (this._activeModel !== modelId) {
            this._activeModel = modelId;
            this._onDidChangeActiveModel.fire(modelId);
            this._client.setActiveModel(modelId);
            this.logService.info(`[Firefly] Active Model: ${modelId}`);
        }
    }

    getAvailableModels(): { id: string; name: string; provider: string }[] {
        return this._availableModels;
    }

    getModelUsage(): IModelUsage[] {
        return this._modelUsage;
    }
}

registerSingleton(IFireflyWorkbenchService, FireflyWorkbenchService, InstantiationType.Delayed);
