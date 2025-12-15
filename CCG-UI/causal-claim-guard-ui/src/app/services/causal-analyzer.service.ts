import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SourcePayload {
  Title?: string | null;
  Url?: string | null;
  Type?: string | null;
  SampleSize?: number | null;
  Year?: number | null;
  PeerReviewed?: boolean | null;
}

export interface AnalyzeRequestPayload {
  TextClaim: string;
  Domain: string;   // "auto" | "health" | "finance"
  Sources: SourcePayload[];
}

export interface AnalyzeResponsePayload {
  TextClaim: string;
  Domain: string;
  Rung: 'L1' | 'L2' | 'L3';
  Template: {
    X: string;
    Y: string;
    Z: string[];
    Edges: [string, string][];
    Note: string;
  };
  Estimand: {
    Identifiable: boolean;
    Expression: string;
    Reason: string;
  };
  SourceTrust: {
    m: number;
    c: number;
    Source?: string | null;
    Details?: string | null;
  }[];
  AggregatedTrust: {
    m: number;
    c: number;
    Source?: string | null;
    Details?: string | null;
  };
  Explanation: string;
}

@Injectable({
  providedIn: 'root'
})
export class CausalAnalyzerService {
  private apiUrl = 'http://localhost:5001/analyze_claim';

  constructor(private http: HttpClient) {}

  analyze(payload: AnalyzeRequestPayload): Observable<AnalyzeResponsePayload> {
    return this.http.post<AnalyzeResponsePayload>(this.apiUrl, payload);
  }
}
