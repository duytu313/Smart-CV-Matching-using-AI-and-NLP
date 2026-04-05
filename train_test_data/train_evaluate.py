import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import seaborn as sns
import json
from datetime import datetime
import os

# Tạo thư mục results nếu chưa có
os.makedirs("results", exist_ok=True)

# Đọc dữ liệu
train_df = pd.read_csv("../data/cv_jd_pairs/train_cv_jd_pairs.csv")
test_df = pd.read_csv("../data/cv_jd_pairs/test_cv_jd_pairs.csv")

# ============================================
# RANKING METRICS: NDCG & MRR
# ============================================
def ndcg_at_k(relevance_scores, k=10):
    """
    Tính NDCG@k (Normalized Discounted Cumulative Gain)
    
    Args:
        relevance_scores: list of relevance scores (0 hoặc 1)
        k: số lượng kết quả top-k
    
    Returns:
        NDCG@k score
    """
    if len(relevance_scores) == 0:
        return 0.0
    
    # Lấy top-k
    relevance_scores = relevance_scores[:k]
    
    # DCG
    dcg = 0.0
    for i, rel in enumerate(relevance_scores):
        dcg += rel / np.log2(i + 2)  # i+2 vì log2(1+1)=log2(2)=1
    
    # IDCG (Ideal DCG)
    ideal_scores = sorted(relevance_scores, reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_scores):
        idcg += rel / np.log2(i + 2)
    
    # NDCG
    if idcg == 0:
        return 0.0
    return dcg / idcg

def mrr_at_k(relevance_scores, k=10):
    """
    Tính MRR@k (Mean Reciprocal Rank)
    
    Args:
        relevance_scores: list of relevance scores (0 hoặc 1)
        k: số lượng kết quả top-k
    
    Returns:
        MRR@k score
    """
    if len(relevance_scores) == 0:
        return 0.0
    
    # Lấy top-k
    relevance_scores = relevance_scores[:k]
    
    # Tìm vị trí đầu tiên có relevance=1
    for i, rel in enumerate(relevance_scores):
        if rel == 1:
            return 1.0 / (i + 1)
    
    return 0.0

def evaluate_ranking_metrics(model_scores, y_true, k_values=[1, 3, 5, 10]):
    """
    Đánh giá ranking metrics cho tất cả các queries
    
    Args:
        model_scores: array of similarity scores
        y_true: ground truth labels (0/1)
        k_values: list of k values for NDCG@k and MRR@k
    
    Returns:
        Dictionary với các metrics
    """
    metrics = {}
    
    # Với mỗi sample, coi như 1 query riêng
    # Sắp xếp theo score giảm dần để tính ranking
    for k in k_values:
        ndcg_scores = []
        mrr_scores = []
        
        # Trong trường hợp này, mỗi cặp (CV, JD) là độc lập
        # Nên chúng ta tính NDCG và MRR dựa trên thứ tự sắp xếp theo score
        # Sắp xếp tất cả samples theo score giảm dần
        sorted_indices = np.argsort(model_scores)[::-1]
        sorted_relevance = y_true.iloc[sorted_indices].values if hasattr(y_true, 'iloc') else y_true[sorted_indices]
        
        # Tính NDCG@k
        ndcg = ndcg_at_k(sorted_relevance, k)
        metrics[f"NDCG@{k}"] = ndcg
        
        # Tính MRR@k
        mrr = mrr_at_k(sorted_relevance, k)
        metrics[f"MRR@{k}"] = mrr
    
    return metrics

def evaluate_ranking_per_query(model_scores_df, y_true_df, k_values=[1, 3, 5, 10]):
    """
    Đánh giá ranking metrics theo từng CV (mỗi CV có nhiều JD)
    
    Args:
        model_scores_df: DataFrame với các cột ['cv_id', 'jd_id', 'score']
        y_true_df: DataFrame với các cột ['cv_id', 'jd_id', 'label']
        k_values: list of k values
    
    Returns:
        Dictionary với average metrics
    """
    metrics = {f"NDCG@{k}": [] for k in k_values}
    metrics.update({f"MRR@{k}": [] for k in k_values})
    
    # Group by cv_id
    for cv_id in model_scores_df['cv_id'].unique():
        # Lấy tất cả JD cho CV này
        cv_scores = model_scores_df[model_scores_df['cv_id'] == cv_id].copy()
        cv_labels = y_true_df[y_true_df['cv_id'] == cv_id].copy()
        
        # Merge scores với labels
        merged = cv_scores.merge(cv_labels[['jd_id', 'label']], on='jd_id', how='left')
        merged['label'] = merged['label'].fillna(0)
        
        # Sắp xếp theo score giảm dần
        merged = merged.sort_values('score', ascending=False)
        relevance_scores = merged['label'].values
        
        # Tính metrics cho từng k
        for k in k_values:
            metrics[f"NDCG@{k}"].append(ndcg_at_k(relevance_scores, k))
            metrics[f"MRR@{k}"].append(mrr_at_k(relevance_scores, k))
    
    # Tính average
    avg_metrics = {}
    for k in k_values:
        avg_metrics[f"NDCG@{k}"] = np.mean(metrics[f"NDCG@{k}"])
        avg_metrics[f"MRR@{k}"] = np.mean(metrics[f"MRR@{k}"])
    
    return avg_metrics

# Metrics function (cập nhật)
def evaluate_model(y_true, y_pred, y_score=None, model_name="Model", 
                   ranking_scores=None, cv_ids=None, jd_ids=None):
    """Tính toán đầy đủ các metrics bao gồm classification và ranking"""
    metrics = {
        "Model": model_name,
        "Accuracy": accuracy_score(y_true, y_pred),
        "Precision": precision_score(y_true, y_pred),
        "Recall": recall_score(y_true, y_pred),
        "F1-Score": f1_score(y_true, y_pred),
    }
    
    if y_score is not None:
        metrics["AUC-ROC"] = roc_auc_score(y_true, y_score)
    
    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    metrics["Confusion_Matrix_TN"] = cm[0,0]
    metrics["Confusion_Matrix_FP"] = cm[0,1]
    metrics["Confusion_Matrix_FN"] = cm[1,0]
    metrics["Confusion_Matrix_TP"] = cm[1,1]
    
    # Ranking Metrics
    if ranking_scores is not None and cv_ids is not None and jd_ids is not None:
        # Tạo DataFrame cho ranking
        ranking_df = pd.DataFrame({
            'cv_id': cv_ids,
            'jd_id': jd_ids,
            'score': ranking_scores
        })
        y_true_df = pd.DataFrame({
            'cv_id': cv_ids,
            'jd_id': jd_ids,
            'label': y_true
        })
        
        # Tính ranking metrics
        ranking_metrics = evaluate_ranking_per_query(ranking_df, y_true_df, k_values=[1, 3, 5, 10])
        metrics.update(ranking_metrics)
    
    print(f"\n{'='*50}")
    print(f"📊 {model_name} Results")
    print(f"{'='*50}")
    for metric, value in metrics.items():
        if metric not in ["Model", "Confusion_Matrix_TN", "Confusion_Matrix_FP", 
                          "Confusion_Matrix_FN", "Confusion_Matrix_TP"]:
            if metric.startswith(("NDCG", "MRR")):
                print(f"{metric:12s}: {value:.4f}")
            else:
                print(f"{metric:12s}: {value:.4f}")
    
    print(f"\nConfusion Matrix:")
    print(f"TN: {cm[0,0]:4d}  FP: {cm[0,1]:4d}")
    print(f"FN: {cm[1,0]:4d}  TP: {cm[1,1]:4d}")
    
    return metrics

# ============================================
# MODEL 1: TF-IDF + Cosine Similarity
# ============================================
def tfidf_model(train_df, test_df):
    print("\n🔄 Training TF-IDF model...")
    
    # Vectorize CV và JD
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    
    # Fit trên train CVs
    all_cvs = list(train_df['cv_text']) + list(test_df['cv_text'])
    vectorizer.fit(all_cvs)
    
    # Transform
    train_cv_vec = vectorizer.transform(train_df['cv_text'])
    train_jd_vec = vectorizer.transform(train_df['jd_text'])
    test_cv_vec = vectorizer.transform(test_df['cv_text'])
    test_jd_vec = vectorizer.transform(test_df['jd_text'])
    
    # Tính similarity
    train_sim = cosine_similarity(train_cv_vec, train_jd_vec).diagonal()
    test_sim = cosine_similarity(test_cv_vec, test_jd_vec).diagonal()
    
    # Tìm threshold tốt nhất trên train set
    thresholds = np.arange(0.1, 0.9, 0.05)
    best_thresh = 0.5
    best_f1 = 0
    
    for thresh in thresholds:
        pred_train = (train_sim > thresh).astype(int)
        f1 = f1_score(train_df['label'], pred_train)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh
    
    print(f"✅ Best threshold: {best_thresh:.3f} (F1: {best_f1:.4f})")
    
    # Predict trên test
    y_pred = (test_sim > best_thresh).astype(int)
    metrics = evaluate_model(
        test_df['label'], y_pred, test_sim, "TF-IDF + Cosine",
        ranking_scores=test_sim, 
        cv_ids=test_df['cv_id'].values, 
        jd_ids=test_df['jd_id'].values
    )
    metrics["Best_Threshold"] = best_thresh
    return metrics

# ============================================
# MODEL 2: Word2Vec + Average Embedding
# ============================================
def word2vec_model(train_df, test_df):
    print("\n🔄 Training Word2Vec model...")
    
    # Chuẩn bị corpus từ CV và JD
    corpus = []
    for text in list(train_df['cv_text']) + list(train_df['jd_text']):
        corpus.append(simple_preprocess(text))
    
    # Train Word2Vec
    w2v_model = Word2Vec(sentences=corpus, vector_size=300, window=5, min_count=1, workers=4)
    
    def get_doc_vector(text):
        words = simple_preprocess(text)
        vectors = [w2v_model.wv[word] for word in words if word in w2v_model.wv]
        if len(vectors) == 0:
            return np.zeros(300)
        return np.mean(vectors, axis=0)
    
    # Tính similarity
    def compute_similarities(df):
        similarities = []
        for idx, row in df.iterrows():
            cv_vec = get_doc_vector(row['cv_text'])
            jd_vec = get_doc_vector(row['jd_text'])
            sim = cosine_similarity([cv_vec], [jd_vec])[0][0]
            similarities.append(sim)
        return np.array(similarities)
    
    train_sim = compute_similarities(train_df)
    test_sim = compute_similarities(test_df)
    
    # Tìm threshold
    thresholds = np.arange(0.1, 0.9, 0.05)
    best_thresh = 0.5
    best_f1 = 0
    
    for thresh in thresholds:
        pred_train = (train_sim > thresh).astype(int)
        f1 = f1_score(train_df['label'], pred_train)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh
    
    print(f"✅ Best threshold: {best_thresh:.3f} (F1: {best_f1:.4f})")
    
    y_pred = (test_sim > best_thresh).astype(int)
    metrics = evaluate_model(
        test_df['label'], y_pred, test_sim, "Word2Vec + Average",
        ranking_scores=test_sim,
        cv_ids=test_df['cv_id'].values,
        jd_ids=test_df['jd_id'].values
    )
    metrics["Best_Threshold"] = best_thresh
    return metrics

# ============================================
# MODEL 3: SBERT (Pretrained - no fine-tune)
# ============================================
def sbert_pretrained_model(test_df):
    print("\n🔄 Loading pretrained SBERT model...")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Encode và tính similarity
    def compute_sbert_similarity(df):
        cv_embeddings = model.encode(df['cv_text'].tolist(), show_progress_bar=True)
        jd_embeddings = model.encode(df['jd_text'].tolist(), show_progress_bar=True)
        
        similarities = []
        for i in range(len(df)):
            sim = cosine_similarity([cv_embeddings[i]], [jd_embeddings[i]])[0][0]
            similarities.append(sim)
        return np.array(similarities)
    
    test_sim = compute_sbert_similarity(test_df)
    
    # Threshold tối ưu (có thể dùng 0.5 hoặc tìm trên validation)
    y_pred = (test_sim > 0.5).astype(int)
    metrics = evaluate_model(
        test_df['label'], y_pred, test_sim, "SBERT (Pretrained)",
        ranking_scores=test_sim,
        cv_ids=test_df['cv_id'].values,
        jd_ids=test_df['jd_id'].values
    )
    return metrics

# ============================================
# MODEL 4: SBERT Fine-tuned
# ============================================
def sbert_finetuned_model(train_df, test_df):
    print("\n🔄 Fine-tuning SBERT model...")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Chuẩn bị dữ liệu train
    train_examples = []
    for idx, row in train_df.iterrows():
        train_examples.append(InputExample(texts=[row['cv_text'], row['jd_text']], label=float(row['label'])))
    
    # DataLoader
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
    
    # Loss function: CosineSimilarityLoss
    train_loss = losses.CosineSimilarityLoss(model)
    
    # Fine-tune (3 epochs)
    print("Fine-tuning in progress...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=3,
        warmup_steps=100,
        show_progress_bar=True
    )
    
    # Đánh giá trên test
    test_cv_emb = model.encode(test_df['cv_text'].tolist(), show_progress_bar=True)
    test_jd_emb = model.encode(test_df['jd_text'].tolist(), show_progress_bar=True)
    
    test_sim = []
    for i in range(len(test_df)):
        sim = cosine_similarity([test_cv_emb[i]], [test_jd_emb[i]])[0][0]
        test_sim.append(sim)
    test_sim = np.array(test_sim)
    
    y_pred = (test_sim > 0.5).astype(int)
    metrics = evaluate_model(
        test_df['label'], y_pred, test_sim, "SBERT (Fine-tuned)",
        ranking_scores=test_sim,
        cv_ids=test_df['cv_id'].values,
        jd_ids=test_df['jd_id'].values
    )
    
    # Save model
    model.save("results/sbert_finetuned_cv_jd")
    print("✅ Model saved to 'results/sbert_finetuned_cv_jd'")
    
    return metrics

# ============================================
# VISUALIZATION & SAVE RESULTS
# ============================================
def save_results(all_metrics, train_df, test_df):
    """Lưu toàn bộ kết quả vào file"""
    
    # 1. Chuyển metrics thành DataFrame
    metrics_df = pd.DataFrame(all_metrics)
    
    # 2. Lưu metrics chi tiết vào CSV
    metrics_df.to_csv("results/model_metrics.csv", index=False)
    print("\n✅ Saved metrics to 'results/model_metrics.csv'")
    
    # 3. Lưu dưới dạng JSON
    metrics_json = metrics_df.to_dict(orient='records')
    with open("results/model_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(metrics_json, f, indent=2, ensure_ascii=False)
    print("✅ Saved metrics to 'results/model_metrics.json'")
    
    # 4. Tạo báo cáo text
    with open("results/evaluation_report.txt", 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("CV-JD MATCHING MODEL EVALUATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"Dataset Statistics:\n")
        f.write(f"- Train samples: {len(train_df)}\n")
        f.write(f"- Test samples: {len(test_df)}\n")
        f.write(f"- Match ratio: {test_df['label'].mean()*100:.1f}%\n\n")
        
        f.write("Model Performance Summary:\n")
        f.write("-"*60 + "\n")
        
        for _, row in metrics_df.iterrows():
            f.write(f"\n{row['Model']}:\n")
            f.write(f"  Accuracy : {row['Accuracy']:.4f}\n")
            f.write(f"  Precision: {row['Precision']:.4f}\n")
            f.write(f"  Recall   : {row['Recall']:.4f}\n")
            f.write(f"  F1-Score : {row['F1-Score']:.4f}\n")
            if 'AUC-ROC' in row:
                f.write(f"  AUC-ROC  : {row['AUC-ROC']:.4f}\n")
            # Ranking metrics
            for metric in ['NDCG@1', 'NDCG@3', 'NDCG@5', 'NDCG@10', 
                          'MRR@1', 'MRR@3', 'MRR@5', 'MRR@10']:
                if metric in row:
                    f.write(f"  {metric:8s}: {row[metric]:.4f}\n")
        
        # Best model based on F1-Score
        best_idx = metrics_df['F1-Score'].idxmax()
        best_model = metrics_df.loc[best_idx, 'Model']
        best_f1 = metrics_df.loc[best_idx, 'F1-Score']
        f.write(f"\n{'='*60}\n")
        f.write(f"🏆 BEST MODEL (F1-Score): {best_model} (F1-Score: {best_f1:.4f})\n")
        
        # Best model based on NDCG@10
        if 'NDCG@10' in metrics_df.columns:
            best_ndcg_idx = metrics_df['NDCG@10'].idxmax()
            best_ndcg_model = metrics_df.loc[best_ndcg_idx, 'Model']
            best_ndcg = metrics_df.loc[best_ndcg_idx, 'NDCG@10']
            f.write(f"🏆 BEST MODEL (NDCG@10): {best_ndcg_model} (NDCG@10: {best_ndcg:.4f})\n")
        
        f.write("="*60 + "\n")
    
    print("✅ Saved report to 'results/evaluation_report.txt'")
    
    # 5. Vẽ và lưu biểu đồ
    plot_comparison(metrics_df)
    
    return metrics_df

def plot_comparison(metrics_df):
    """Vẽ biểu đồ so sánh các models và lưu"""
    
    # Classification metrics
    class_metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
    if 'AUC-ROC' in metrics_df.columns:
        class_metrics.append('AUC-ROC')
    
    # Ranking metrics
    ranking_metrics = [m for m in metrics_df.columns if m.startswith(('NDCG', 'MRR'))]
    
    # Figure 1: Bar chart for classification metrics
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    metrics_df.set_index('Model')[class_metrics].plot(kind='bar', ax=ax1)
    ax1.set_title('Model Comparison - Classification Metrics', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Score', fontsize=12)
    ax1.set_xlabel('Model', fontsize=12)
    ax1.legend(loc='lower right')
    ax1.set_ylim([0, 1])
    ax1.grid(True, alpha=0.3)
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('results/classification_metrics_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved classification metrics chart to 'results/classification_metrics_comparison.png'")
    
    # Figure 2: NDCG@k comparison
    if ranking_metrics:
        ndcg_metrics = [m for m in ranking_metrics if m.startswith('NDCG')]
        if ndcg_metrics:
            fig2, ax2 = plt.subplots(figsize=(12, 6))
            metrics_df.set_index('Model')[ndcg_metrics].plot(kind='bar', ax=ax2)
            ax2.set_title('Model Comparison - NDCG@k (Higher is Better)', fontsize=14, fontweight='bold')
            ax2.set_ylabel('NDCG Score', fontsize=12)
            ax2.set_xlabel('Model', fontsize=12)
            ax2.legend(loc='lower right')
            ax2.set_ylim([0, 1])
            ax2.grid(True, alpha=0.3)
            ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig('results/ndcg_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("✅ Saved NDCG comparison chart to 'results/ndcg_comparison.png'")
        
        # Figure 3: MRR@k comparison
        mrr_metrics = [m for m in ranking_metrics if m.startswith('MRR')]
        if mrr_metrics:
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            metrics_df.set_index('Model')[mrr_metrics].plot(kind='bar', ax=ax3)
            ax3.set_title('Model Comparison - MRR@k (Higher is Better)', fontsize=14, fontweight='bold')
            ax3.set_ylabel('MRR Score', fontsize=12)
            ax3.set_xlabel('Model', fontsize=12)
            ax3.legend(loc='lower right')
            ax3.set_ylim([0, 1])
            ax3.grid(True, alpha=0.3)
            ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig('results/mrr_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("✅ Saved MRR comparison chart to 'results/mrr_comparison.png'")
    
    # Figure 4: F1-Score horizontal bar
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    metrics_df_sorted = metrics_df.sort_values('F1-Score', ascending=True)
    colors = plt.cm.viridis(np.linspace(0, 1, len(metrics_df_sorted)))
    ax4.barh(metrics_df_sorted['Model'], metrics_df_sorted['F1-Score'], color=colors)
    ax4.set_xlabel('F1-Score', fontsize=12)
    ax4.set_title('F1-Score Comparison (Higher is Better)', fontsize=14, fontweight='bold')
    ax4.set_xlim([0, 1])
    ax4.grid(True, alpha=0.3, axis='x')
    
    # Thêm giá trị trên thanh
    for i, (idx, row) in enumerate(metrics_df_sorted.iterrows()):
        ax4.text(row['F1-Score'] + 0.01, i, f'{row["F1-Score"]:.4f}', va='center')
    
    plt.tight_layout()
    plt.savefig('results/f1_score_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved F1-Score chart to 'results/f1_score_comparison.png'")
    
    # Figure 5: Heatmap cho ranking metrics
    if ranking_metrics:
        fig5, ax5 = plt.subplots(figsize=(12, 8))
        heatmap_data = metrics_df.set_index('Model')[ranking_metrics]
        sns.heatmap(heatmap_data, annot=True, fmt='.4f', cmap='YlOrRd', 
                    cbar_kws={'label': 'Score'}, ax=ax5)
        ax5.set_title('Ranking Metrics Heatmap', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig('results/ranking_metrics_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ Saved ranking metrics heatmap to 'results/ranking_metrics_heatmap.png'")

# ============================================
# RUN ALL MODELS
# ============================================
if __name__ == "__main__":
    print("="*60)
    print("🎯 CV-JD MATCHING MODEL EVALUATION")
    print("="*60)
    print(f"Train samples: {len(train_df)}")
    print(f"Test samples: {len(test_df)}")
    print(f"Match ratio in test: {test_df['label'].mean()*100:.1f}%")
    print("="*60)
    
    all_metrics = []
    
    # Chạy từng model
    all_metrics.append(tfidf_model(train_df, test_df))
    all_metrics.append(word2vec_model(train_df, test_df))
    all_metrics.append(sbert_pretrained_model(test_df))
    all_metrics.append(sbert_finetuned_model(train_df, test_df))
    
    # Lưu kết quả
    metrics_df = save_results(all_metrics, train_df, test_df)
    
    # In summary
    print("\n" + "="*60)
    print("📈 FINAL COMPARISON SUMMARY")
    print("="*60)
    
    # Classification summary
    class_cols = ['Model', 'Accuracy', 'Precision', 'Recall', 'F1-Score']
    if 'AUC-ROC' in metrics_df.columns:
        class_cols.append('AUC-ROC')
    print("\nClassification Metrics:")
    print(metrics_df[class_cols].round(4))
    
    # Ranking summary
    ranking_cols = ['Model'] + [c for c in metrics_df.columns if c.startswith(('NDCG', 'MRR'))]
    if len(ranking_cols) > 1:
        print("\nRanking Metrics:")
        print(metrics_df[ranking_cols].round(4))
    
    print("="*60)
    
    # Best models
    best_f1_idx = metrics_df['F1-Score'].idxmax()
    best_model_f1 = metrics_df.loc[best_f1_idx, 'Model']
    best_f1 = metrics_df.loc[best_f1_idx, 'F1-Score']
    print(f"\n🏆 Best Model (F1-Score): {best_model_f1} (F1-Score: {best_f1:.4f})")
    
    if 'NDCG@10' in metrics_df.columns:
        best_ndcg_idx = metrics_df['NDCG@10'].idxmax()
        best_model_ndcg = metrics_df.loc[best_ndcg_idx, 'Model']
        best_ndcg = metrics_df.loc[best_ndcg_idx, 'NDCG@10']
        print(f"🏆 Best Model (NDCG@10): {best_model_ndcg} (NDCG@10: {best_ndcg:.4f})")
    
    print("\n✅ All results saved to 'results/' folder")