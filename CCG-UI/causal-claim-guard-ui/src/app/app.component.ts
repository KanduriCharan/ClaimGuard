import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  CausalAnalyzerService,
  AnalyzeResponsePayload,
  SourcePayload
} from './services/causal-analyzer.service';

interface DagNode {
  id: string;           // variable name (e.g., "coffee", "sleep quality")
  label: string;        // label shown in the pill
  kind: 'X' | 'Y' | 'Z';
  x: number;
  y: number;
}

interface DagEdge {
  from: string;
  to: string;
}


@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'CausalClaim Guard';
  private analyzer = inject(CausalAnalyzerService);
  // form fields
  claim = '';
  domain = 'auto';
  sourceType = '';
  sourceUrl = '';
  sourceTitle = '';
  sourceYear: number | null = null;
  sampleSize: number | null = null;

  // UI state
  loading = false;
  statusText = 'Idle · waiting for a claim';
  backendStatus = 'connected';

  result: AnalyzeResponsePayload | null = null;

    // --- DAG helpers ---

    get dagNodes(): DagNode[] {
      const tpl = this.result?.Template;
      if (!tpl) return [];
  
      const nodes: DagNode[] = [];
  
      // X node (left center)
      nodes.push({
        id: tpl.X,
        label: 'X: ' + tpl.X,
        kind: 'X',
        x: 80,
        y: 90
      });
  
      // Y node (right center)
      nodes.push({
        id: tpl.Y,
        label: 'Y: ' + tpl.Y,
        kind: 'Y',
        x: 260,
        y: 90
      });
  
      // Z nodes (spread top/bottom)
      const zs = tpl.Z || [];
      const topY = 30;
      const bottomY = 150;
  
      zs.forEach((z, index) => {
        const isTop = index % 2 === 0;
        const rowIndex = Math.floor(index / 2);
        const xBase = 80 + rowIndex * 80; // stagger horizontally
  
        nodes.push({
          id: z,
          label: 'Z: ' + z,
          kind: 'Z',
          x: xBase,
          y: isTop ? topY : bottomY
        });
      });
  
      return nodes;
    }
  
    get dagEdges(): DagEdge[] {
      const tpl = this.result?.Template;
      if (!tpl || !tpl.Edges) return [];
      return tpl.Edges.map(([from, to]) => ({ from, to }));
    }
  
    getNodeFor(name: string): DagNode | undefined {
      return this.dagNodes.find((n) => n.id === name);
    }
  

  constructor() {}

  get rungLabel(): string {
    if (!this.result) return 'L1 · Association';
    const rung = this.result.Rung;
    if (rung === 'L2') return 'L2 · Intervention';
    if (rung === 'L3') return 'L3 · Counterfactual';
    return 'L1 · Association';
  }

  get rungClass(): string {
    if (!this.result) return 'badge-rung-l1';
    if (this.result.Rung === 'L2') return 'badge-rung-l2';
    if (this.result.Rung === 'L3') return 'badge-rung-l3';
    return 'badge-rung-l1';
  }

  get trustPercent(): number {
    if (!this.result) return 0;
    return Math.round(this.result.AggregatedTrust.m * 100);
  }

  get confPercent(): number {
    if (!this.result) return 0;
    return Math.round(this.result.AggregatedTrust.c * 100);
  }

  get trustHint(): string {
    if (!this.result) {
      return 'No sources provided · T(m, c) defaults to (0, 0) = complete uncertainty.';
    }
    const agg = this.result.AggregatedTrust;
    if (agg.m === 0 && agg.c === 0 && (agg.Details || '').includes('no sources')) {
      return 'No sources provided · T(m, c) = (0, 0) → complete uncertainty about evidence.';
    }
    return `Aggregated trust T(m, c) = (${agg.m.toFixed(2)}, ${agg.c.toFixed(2)}) · ${agg.Details ?? ''}`;
  }

  runAnalysis(): void {
    const trimmed = this.claim.trim();
    if (!trimmed) {
      this.statusText = 'Please enter a claim before running analysis.';
      return;
    }

    const sources: SourcePayload[] = [];
    if (this.sourceUrl.trim()) {
      sources.push({
        Title: this.sourceTitle.trim() || null,
        Url: this.sourceUrl.trim(),
        Type: this.sourceType || null,
        SampleSize: this.sampleSize ?? null,
        Year: this.sourceYear ?? null,
        PeerReviewed: this.sourceType === 'peer-reviewed'
      });
    }

    const domainPayload = this.domain === 'auto' ? 'auto' : this.domain;

    const payload = {
      TextClaim: trimmed,
      Domain: domainPayload,
      Sources: sources
    };

    this.loading = true;
    this.statusText = 'Analyzing claim…';

    this.analyzer.analyze(payload).subscribe({
      next: (res) => {
        this.result = res;
        this.statusText = 'Analysis complete.';
        this.backendStatus = 'connected';
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.statusText = 'Error during analysis. Check backend.';
        this.backendStatus = 'error';
        this.loading = false;
      }
    });
  }
}
