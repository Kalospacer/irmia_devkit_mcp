import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Collections;
import java.util.Locale;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.SimpleJavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import com.sun.source.util.JavacTask;

/** 只调用 JDK 解析阶段，不校验依赖、类名文件匹配或生成目标代码。 */
public final class IrmiaSyntaxParser {
    public static void main(String[] args) throws Exception {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            System.err.println("JDK compiler unavailable");
            System.exit(2);
        }
        final String source = new String(Files.readAllBytes(Paths.get(args[0])), Charset.forName(args[1]));
        final String content = source.startsWith("\uFEFF") ? source.substring(1) : source;
        JavaFileObject unit = new SimpleJavaFileObject(Paths.get(args[0]).toUri(), JavaFileObject.Kind.SOURCE) {
            @Override
            public CharSequence getCharContent(boolean ignoreEncodingErrors) throws IOException {
                return content;
            }
        };
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        boolean failed = false;
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(diagnostics, Locale.ROOT, Charset.forName("UTF-8"))) {
            JavacTask task = (JavacTask) compiler.getTask(null, manager, diagnostics,
                    Arrays.asList("-proc:none"), null, Collections.singletonList(unit));
            task.parse();
            for (Diagnostic<? extends JavaFileObject> diagnostic : diagnostics.getDiagnostics()) {
                if (diagnostic.getKind() == Diagnostic.Kind.ERROR) {
                    failed = true;
                    System.out.println(diagnostic.getLineNumber() + ":" + diagnostic.getColumnNumber() + ":"
                            + diagnostic.getMessage(Locale.ROOT).replace('\n', ' ').replace('\r', ' '));
                }
            }
        }
        System.exit(failed ? 1 : 0);
    }
}
