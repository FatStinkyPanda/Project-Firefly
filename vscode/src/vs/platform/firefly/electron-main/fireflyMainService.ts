/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { IFireflyMainService, IFireflyStatus } from './firefly.js';
import { Emitter } from '../../../base/common/event.js';
import { Disposable } from '../../../base/common/lifecycle.js';
import { ILogService } from '../../log/common/log.js';
import { IEnvironmentMainService } from '../../environment/electron-main/environmentMainService.js';
import { spawn, ChildProcess } from 'child_process';
import { join } from '../../../base/common/path.js';
import { isWindows } from '../../../base/common/platform.js';

export class FireflyMainService extends Disposable implements IFireflyMainService {

    readonly _serviceBrand: undefined;

    private readonly _onDidChangeStatus = this._register(new Emitter<IFireflyStatus>());
    readonly onDidChangeStatus = this._onDidChangeStatus.event;

    private _status: IFireflyStatus = { agentRunning: false, totalCost: 0, isAutonomous: false };
    private _agentProcess?: ChildProcess;

    constructor(
        @ILogService private readonly logService: ILogService,
        @IEnvironmentMainService private readonly environmentMainService: IEnvironmentMainService
    ) {
        super();
        this.logService.info('[Firefly] Initializing Core Intelligence...');
        this.startAgent();
    }

    getStatus(): IFireflyStatus {
        return this._status;
    }

    async reloadAgent(): Promise<void> {
        this.logService.info('[Firefly] Reloading Agent Manager...');
        this.stopAgent();
        this.startAgent();
    }

    setAutonomousMode(enabled: boolean): void {
        this._status = { ...this._status, isAutonomous: enabled };
        this._onDidChangeStatus.fire(this._status);
        this.sendCommand('set_mode', { autonomous: enabled });
    }

    sendIntent(id: string, args: any[]): void {
        this.sendCommand('intent', { id, args });
    }

    async createAgent(name: string, persona: string): Promise<string> {
        this.logService.info(`[Firefly] Creating Agent: ${name} (Persona: ${persona})`);
        const id = Math.random().toString(36).substring(7);
        this.sendCommand('create_agent', { id, name, persona });
        return id;
    }

    async deleteAgent(id: string): Promise<void> {
        this.logService.info(`[Firefly] Deleting Agent: ${id}`);
        this.sendCommand('delete_agent', { id });
    }

    setSafetyMode(mode: string): void {
        this.logService.info(`[Firefly] Safety Mode -> ${mode}`);
        this.sendCommand('set_safety_mode', { mode });
    }

    setActiveModel(modelId: string): void {
        this.logService.info(`[Firefly] Active Model -> ${modelId}`);
        this.sendCommand('set_active_model', { model_id: modelId });
    }

    sendChat(text: string): void {
        this.sendCommand('chat', { text });
    }


    private sendCommand(type: string, payload: any): void {
        if (this._agentProcess?.stdin?.writable) {
            const command = JSON.stringify({ type, ...payload }) + '\n';
            this._agentProcess.stdin.write(command);
        } else {
            this.logService.warn(`[Firefly] Cannot send command ${type}: Agent process stdin not available.`);
        }
    }

    private startAgent(): void {
        const pythonPath = isWindows ? 'python' : 'python3';
        // Assume agent_manager is in the same root as the vscode folder
        const agentPath = join(this.environmentMainService.appRoot, '..', 'agent_manager', 'main_controller.py');

        this.logService.info(`[Firefly] Spawning Agent Backend: ${pythonPath} ${agentPath}`);

        try {
            const projectRoot = join(this.environmentMainService.appRoot, '..');
            this._agentProcess = spawn(pythonPath, [agentPath], {
                cwd: projectRoot,
                env: { ...process.env, "FIREFLY_IDE_MODE": "true", "PYTHONPATH": projectRoot }
            });

            this._status = { ...this._status, agentRunning: true };
            this._onDidChangeStatus.fire(this._status);

            this._agentProcess.on('exit', (code) => {
                this.logService.warn(`[Firefly] Agent Backend exited with code ${code}`);
                this._status = { ...this._status, agentRunning: false };
                this._onDidChangeStatus.fire(this._status);
            });

            this._agentProcess.stdout?.on('data', (data) => {
                const output = data.toString();

                // Advanced Status Parsing: [FIREFLY:STATUS] thought="..." cost=... mode=...
                if (output.includes('[FIREFLY:STATUS]')) {
                    const statusLine = output.split('\n').find((l: string) => l.includes('[FIREFLY:STATUS]'));
                    if (statusLine) {
                        const thoughtMatch = statusLine.match(/thought="([^"]+)"/);
                        const costMatch = statusLine.match(/cost=([\d.]+)/);
                        const modeMatch = statusLine.match(/mode=([^ ]+)/);

                        const newStatus: any = {};
                        if (thoughtMatch) newStatus.currentThought = thoughtMatch[1];
                        if (costMatch) newStatus.totalCost = parseFloat(costMatch[1]);
                        if (modeMatch) newStatus.isAutonomous = modeMatch[1].toLowerCase() === 'autonomous';

                        this._status = { ...this._status, ...newStatus };
                        this._onDidChangeStatus.fire(this._status);
                    }
                } else if (output.includes('"thought":')) {
                    // Legacy/Fallback parsing
                    try {
                        const match = output.match(/"thought":\s*"([^"]+)"/);
                        if (match) {
                            this._status = { ...this._status, currentThought: match[1] };
                            this._onDidChangeStatus.fire(this._status);
                        }
                    } catch { }
                }
            });

        } catch (e) {
            this.logService.error('[Firefly] Failed to start Agent Backend', e);
        }
    }

    private stopAgent(): void {
        if (this._agentProcess) {
            this._agentProcess.kill();
            this._agentProcess = undefined;
        }
    }

    override dispose(): void {
        this.stopAgent();
        super.dispose();
    }
}
