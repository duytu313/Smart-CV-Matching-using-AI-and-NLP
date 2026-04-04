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

# Metrics function
def evaluate_model(y_true, y_pred, y_score=None, model_name="Model"):
    """Tính toán đầy đủ các metrics"""
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
    
    print(f"\n{'='*50}")
    print(f"📊 {model_name} Results")
    print(f"{'='*50}")
    for metric, value in metrics.items():
        if metric not in ["Model", "Confusion_Matrix_TN", "Confusion_Matrix_FP", "Confusion_Matrix_FN", "Confusion_Matrix_TP"]:
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
    metrics = evaluate_model(test_df['label'], y_pred, test_sim, "TF-IDF + Cosine")
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
    metrics = evaluate_model(test_df['label'], y_pred, test_sim, "Word2Vec + Average")
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
    metrics = evaluate_model(test_df['label'], y_pred, test_sim, "SBERT (Pretrained)")
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
    metrics = evaluate_model(test_df['label'], y_pred, test_sim, "SBERT (Fine-tuned)")
    
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
        
        # Best model
        best_idx = metrics_df['F1-Score'].idxmax()
        best_model = metrics_df.loc[best_idx, 'Model']
        best_f1 = metrics_df.loc[best_idx, 'F1-Score']
        f.write(f"\n{'='*60}\n")
        f.write(f"🏆 BEST MODEL: {best_model} (F1-Score: {best_f1:.4f})\n")
        f.write("="*60 + "\n")
    
    print("✅ Saved report to 'results/evaluation_report.txt'")
    
    # 5. Vẽ và lưu biểu đồ
    plot_comparison(metrics_df)
    
    return metrics_df

def plot_comparison(metrics_df):
    """Vẽ biểu đồ so sánh các models và lưu"""
    
    # Bỏ AUC-ROC nếu không có
    plot_metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
    if 'AUC-ROC' in metrics_df.columns:
        plot_metrics.append('AUC-ROC')
    
    # Figure 1: Bar chart comparison
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    metrics_df.set_index('Model')[plot_metrics].plot(kind='bar', ax=ax1)
    ax1.set_title('Model Comparison - All Metrics', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Score', fontsize=12)
    ax1.set_xlabel('Model', fontsize=12)
    ax1.legend(loc='lower right')
    ax1.set_ylim([0, 1])
    ax1.grid(True, alpha=0.3)
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('results/model_comparison_bar.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved bar chart to 'results/model_comparison_bar.png'")
    
    # Figure 2: F1-Score horizontal bar
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    metrics_df_sorted = metrics_df.sort_values('F1-Score', ascending=True)
    colors = plt.cm.viridis(np.linspace(0, 1, len(metrics_df_sorted)))
    ax2.barh(metrics_df_sorted['Model'], metrics_df_sorted['F1-Score'], color=colors)
    ax2.set_xlabel('F1-Score', fontsize=12)
    ax2.set_title('F1-Score Comparison (Higher is Better)', fontsize=14, fontweight='bold')
    ax2.set_xlim([0, 1])
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Thêm giá trị trên thanh
    for i, (idx, row) in enumerate(metrics_df_sorted.iterrows()):
        ax2.text(row['F1-Score'] + 0.01, i, f'{row["F1-Score"]:.4f}', va='center')
    
    plt.tight_layout()
    plt.savefig('results/f1_score_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved F1-Score chart to 'results/f1_score_comparison.png'")
    
    # Figure 3: Radar chart for top model comparison
    fig3, ax3 = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    models_to_plot = metrics_df['Model'].tolist()
    metrics_to_plot = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
    
    angles = np.linspace(0, 2*np.pi, len(metrics_to_plot), endpoint=False).tolist()
    angles += angles[:1]
    
    for model in models_to_plot:
        values = metrics_df[metrics_df['Model'] == model][metrics_to_plot].values.flatten().tolist()
        values += values[:1]
        ax3.plot(angles, values, 'o-', linewidth=2, label=model)
        ax3.fill(angles, values, alpha=0.1)
    
    ax3.set_xticks(angles[:-1])
    ax3.set_xticklabels(metrics_to_plot)
    ax3.set_ylim([0, 1])
    ax3.set_title('Radar Chart - Model Comparison', fontsize=14, fontweight='bold', pad=20)
    ax3.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax3.grid(True)
    plt.tight_layout()
    plt.savefig('results/radar_chart_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved radar chart to 'results/radar_chart_comparison.png'")
    
    # Figure 4: Heatmap của metrics
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    heatmap_data = metrics_df.set_index('Model')[metrics_to_plot]
    sns.heatmap(heatmap_data, annot=True, fmt='.4f', cmap='YlOrRd', 
                cbar_kws={'label': 'Score'}, ax=ax4)
    ax4.set_title('Performance Heatmap', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('results/performance_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved heatmap to 'results/performance_heatmap.png'")

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
    print(metrics_df[['Model', 'Accuracy', 'Precision', 'Recall', 'F1-Score']].round(4))
    print("="*60)
    
    # Best model
    best_idx = metrics_df['F1-Score'].idxmax()
    best_model = metrics_df.loc[best_idx, 'Model']
    best_f1 = metrics_df.loc[best_idx, 'F1-Score']
    print(f"\n🏆 Best Model: {best_model} (F1-Score: {best_f1:.4f})")
    print("\n✅ All results saved to 'results/' folder")